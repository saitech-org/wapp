#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import pathlib
import re
import subprocess
from typing import Any, Dict, List, Tuple

# ----------------- helpers -----------------

def pascal(s: str) -> str:
    # turn snake/kebab/space into PascalCase
    return "".join(part.capitalize() for part in re.split(r"[_\W]+", s) if part)

def _score_name_quality(s: str) -> int:
    # Prefer names with separators or internal caps (clear word boundaries)
    score = 0
    if any(ch in s for ch in ("_", "-", " ")): score += 2
    if re.search(r"[a-z][A-Z]", s): score += 2  # camel/internal caps
    if s and s[0].isupper(): score += 1
    # Penalize single-capitalized lumps like "Someentity"
    if s.lower() == s or (s[0:1].isupper() and s[1:].islower() and not re.search(r"[a-z][A-Z]", s)):
        score -= 1
    return score

def pick_model_base(schema_base: str | None, resource_seg: str) -> str:
    """
    Choose the better 'base' name to PascalCase:
    - If the schema name has poor boundaries (e.g., 'Someentity'),
      prefer the path segment (e.g., 'some_entity').
    """
    candidates = []
    if schema_base: candidates.append(schema_base)
    candidates.append(resource_seg)  # always consider the path segment

    best = max(candidates, key=_score_name_quality)
    # If we picked the schema lump, but the resource has clearer boundaries, upgrade:
    if best == (schema_base or "") and _score_name_quality(resource_seg) > _score_name_quality(schema_base or ""):
        best = resource_seg
    return pascal(best)

def import_symbol(path: str):
    if ":" in path:
        mod, name = path.split(":", 1)
    else:
        parts = path.split(".")
        mod, name = ".".join(parts[:-1]), parts[-1]
    m = importlib.import_module(mod)
    if not hasattr(m, name):
        raise SystemExit(f"Symbol '{name}' not found in module '{mod}'")
    return getattr(m, name)

def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)

def write_text(path: pathlib.Path, text: str):
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")

def snake(s: str) -> str:
    s = re.sub(r"[^\w]+", "_", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s.lower()

def pascal(s: str) -> str:
    if not s:
        return s
    # If it has separators, do true PascalCase
    parts = [p for p in re.split(r"[_\W]+", s) if p]
    if len(parts) > 1:
        return "".join(p[:1].upper() + p[1:].lower() for p in parts)
    # Single token:
    # If it already contains internal capitals (CamelCase), keep them.
    if re.search(r"[A-Z]", s[1:]):
        return s[0].upper() + s[1:]  # preserve internal caps
    # Else, standard capitalize
    return s.capitalize()

def path_segments(p: str) -> List[str]:
    return [seg for seg in p.split("/") if seg]

def is_success(code: str) -> bool:
    return code == "200" or code == "201" or (len(code) == 3 and code.startswith("2"))

# ----------------- scan openapi once -----------------

class Op:
    def __init__(self, path: str, method: str, op: Dict[str, Any]):
        self.path = path
        self.method = method.upper()
        self.op = op

def scan_ops(spec: Dict[str, Any]) -> List[Op]:
    ops: List[Op] = []
    for p, methods in (spec.get("paths") or {}).items():
        for m, op in (methods or {}).items():
            mu = m.upper()
            if mu in ("GET","POST","PUT","PATCH","DELETE"):
                ops.append(Op(p, mu, op))
    return ops

def find_crud_bases(paths: Dict[str, Any]) -> List[Tuple[str,str]]:
    trailing_slash_bases = { p for p in paths.keys() if p.endswith("/") }
    def last_literal_segment(p: str) -> str | None:
        segs = path_segments(p)
        if not segs: return None
        last = segs[-1]
        return last if "{" not in last else None
    crud = []
    for p in trailing_slash_bases:
        seg = last_literal_segment(p)
        if not seg: continue
        p_id = p.rstrip("/") + "/{id}"
        has = {
            "list":  ("GET",  p),
            "create":("POST", p),
            "get":   ("GET",  p_id),
            "update":("PUT",  p_id),
            "delete":("DELETE",p_id),
        }
        ok = True
        for _, (meth, path_key) in has.items():
            if path_key not in paths or meth.lower() not in paths[path_key]:
                ok = False; break
        if ok:
            crud.append((p, p_id))
    return crud

def first_success_code(op: Dict[str, Any]) -> str | None:
    for code in (op.get("responses") or {}).keys():
        if is_success(code):
            return code
    return None

# ----------------- facade generation -----------------

def model_base_from_schema(sch: Any) -> str | None:
    if not isinstance(sch, dict): return None
    ref = sch.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        title = ref.split("/")[-1]
        m = re.match(r"^(.+?)_(Out|Create|Update)$", title)
        return m.group(1) if m else title
    if sch.get("type") == "array" and isinstance(sch.get("items"), dict):
        return model_base_from_schema(sch["items"])
    return None

def build_facade(openapi: Dict[str, Any]) -> str:
    paths: Dict[str, Any] = openapi.get("paths", {})  # type: ignore
    ops = []
    for p, methods in paths.items():
        for m, op in methods.items():
            m_up = m.upper()
            if m_up not in ("GET","POST","PUT","PATCH","DELETE"): continue
            params = { "path": [], "query": [] }
            for prm in op.get("parameters", []):
                where = prm.get("in")
                if where in ("path","query"):
                    params[where].append(prm)
            rb = op.get("requestBody", {})
            body_schema = None
            if isinstance(rb, dict):
                content = rb.get("content") or {}
                js = content.get("application/json")
                if js and isinstance(js, dict):
                    body_schema = js.get("schema")
            resp_schema = None
            for code, resp in op.get("responses", {}).items():
                if not is_success(code):
                    continue
                content = (resp or {}).get("content") or {}
                js = content.get("application/json")
                if js and isinstance(js, dict):
                    resp_schema = js.get("schema")
                    break
                if code == "204":
                    resp_schema = None
                    break
            ops.append({
                "path": p, "method": m_up, "op": op,
                "params": params, "body_schema": body_schema, "resp_schema": resp_schema
            })

    def last_literal_segment(p: str) -> str | None:
        segs = path_segments(p)
        if not segs: return None
        last = segs[-1]
        return last if "{" not in last else None

    crud_bases = find_crud_bases(paths)
    crud_set = { base for base,_ in crud_bases }

    Tree = dict
    root: Tree = {}

    def ensure(ns: List[str]) -> Tree:
        node = root
        for part in ns:
            node = node.setdefault(part, {})
        return node

    for base, base_id in crud_bases:
        segs = path_segments(base)
        ns = segs[:-1]
        resource = segs[-1]
        list_op = paths[base]["get"]
        resp_model = model_base_from_schema(((list_op.get("responses") or {}).get("200") or {}).get("content", {}).get("application/json", {}).get("schema"))
        leaf = resource
        if resp_model and resp_model.lower() != resource.lower():
            leaf = snake(resp_model)
        node = ensure(ns)
        node[leaf] = {
            "kind": "crud",
            "basePath": base.rstrip("/"),
            "modelBase": resp_model or resource
        }

    for item in ops:
        p = item["path"]
        if any(p == base or p.startswith(base) for base in crud_set):
            continue
        segs = path_segments(p)
        if item["op"].get("summary"):
            func_name = snake(item["op"]["summary"])
        else:
            literals = [s for s in segs if "{" not in s and "}" not in s]
            func_name = snake(literals[-1]) if literals else "op"
        parent_ns = segs[:]
        if func_name and parent_ns and parent_ns[-1].replace("-","_") == func_name:
            parent_ns = parent_ns[:-1]
        node = ensure(parent_ns)
        node[func_name] = {
            "kind": "endpoint",
            "method": item["method"],
            "path": p,
            "pathParams": [pr["name"] for pr in item["params"]["path"]],
            "queryParams": [(pr["name"], pr.get("required", False)) for pr in item["params"]["query"]],
            "hasBody": item["body_schema"] is not None
        }

    out: List[str] = []

    def emit_node(node: Dict[str, Any], depth: int, out: List[str]) -> None:
        indent = "  " * depth
        out.append(f"{indent}{{\n")
        keys = sorted(node.keys())
        for i, key in enumerate(keys):
            val = node[key]
            is_last = (i == len(keys) - 1)
            prop_indent = "  " * (depth + 1)
            if isinstance(val, dict) and val.get("kind") == "crud":
                base = val["basePath"]
                out.append(f"{prop_indent}{key}: {{\n")
                out.append(
                    f"{prop_indent}  list: (query?: {{ page?: number; page_size?: number }}) => client.GET('{base}/', {{ params: {{ query }} }}),\n")
                out.append(
                    f"{prop_indent}  get: (id: number) => client.GET('{base}/{{id}}', {{ params: {{ path: {{ id }} }} }}),\n")
                out.append(
                    f"{prop_indent}  create: (body: paths['{base}/']['post']['requestBody']['content']['application/json']) => client.POST('{base}/', {{ body }}),\n")
                out.append(
                    f"{prop_indent}  update: (id: number, body: paths['{base}/{{id}}']['put']['requestBody']['content']['application/json']) => client.PUT('{base}/{{id}}', {{ params: {{ path: {{ id }} }}, body }}),\n")
                out.append(
                    f"{prop_indent}  delete: (id: number) => client.DELETE('{base}/{{id}}', {{ params: {{ path: {{ id }} }} }}),\n")
                out.append(f"{prop_indent}}}")
                out.append(",\n" if not is_last else "\n")
            elif isinstance(val, dict) and val.get("kind") == "endpoint":
                method = val["method"]
                path = val["path"]
                pparams = val.get("pathParams", [])
                qparams = val.get("queryParams", [])
                has_body = bool(val.get("hasBody"))
                sig_parts: List[str] = []
                call_parts: List[str] = []
                if len(pparams) == 1:
                    pname = pparams[0]
                    sig_parts.append(f"{pname}: any")
                    call_parts.append(f"params: {{ path: {{ {pname} }} }}")
                elif len(pparams) > 1:
                    sig_parts.append("path: { " + ", ".join(f"{n}: any" for n in pparams) + " }")
                    call_parts.append("params: { path }")
                if has_body:
                    body_type = f"paths['{path}']['{method.lower()}']['requestBody']['content']['application/json']"
                    sig_parts.append(f"body: {body_type}")
                if qparams:
                    sig_parts.append("query?: Record<string, any>")
                    if call_parts:
                        call_parts[-1] = call_parts[-1][:-1] + ", query }"
                    else:
                        call_parts.append("params: { query }")
                sig = ", ".join(sig_parts)
                call_obj = ", ".join(call_parts)
                out.append(f"{prop_indent}{key}: ({sig}) => client.{method}('{path}', {{ {call_obj} }})")
                out.append(",\n" if not is_last else "\n")
            else:
                out.append(f"{prop_indent}{key}: ")
                emit_node(val, depth + 2, out)
                out.append("," if not is_last else "")
                out.append("\n")
        out.append(f"{indent}}}")

    out.append("// Auto-generated facade — DO NOT EDIT\n")
    out.append("import type { paths } from './openapi';\n")
    out.append("import { makeClient } from './client';\n\n")
    out.append("export function makeAPI(baseUrl: string, init?: RequestInit) {\n")
    out.append("  const client = makeClient(baseUrl, init);\n")
    out.append("  const API = ")
    emit_node(root, depth=2, out=out)
    out.append(" as const;\n")
    out.append("  return API;\n")
    out.append("}\n")
    return "".join(out)

# ----------------- models.ts generation -----------------

def build_models(openapi: Dict[str, Any]) -> str:
    paths: Dict[str, Any] = openapi.get("paths", {})  # type: ignore
    crud = find_crud_bases(paths)
    crud_set = { base for base,_ in crud }
    out: List[str] = []
    out.append("// Auto-generated models — DO NOT EDIT\n")
    out.append("import type { paths } from './openapi';\n\n")

    def emit(alias: str, rhs: str):
        out.append(f"export type {alias} = {rhs};\n")

    # CRUD model aliases
    for base, base_id in crud:
        # Try to infer a friendly model name from the list response; if not, fall back to last segment.
        list_schema = (paths[base]["get"].get("responses") or {}).get("200", {})
        resource_seg = path_segments(base)[-1]  # e.g., 'some_entity'
        schema_base = model_base_from_schema(
            ((list_schema.get("content") or {}).get("application/json") or {}).get("schema"))
        Model = pick_model_base(schema_base, resource_seg)  # -> 'SomeEntity'
        ListAlias = f"{Model}ListResponse"
        GetAlias  = f"{Model}GetResponse"
        CreateReq = f"{Model}CreateRequest"
        CreateRes = f"{Model}CreateResponse"
        UpdateReq = f"{Model}UpdateRequest"
        UpdateRes = f"{Model}UpdateResponse"
        DeleteRes = f"{Model}DeleteResponse"
        ItemAlias = f"{Model}"

        list_rhs   = f"paths['{base}']['get']['responses']['200']['content']['application/json']"
        get_rhs    = f"paths['{base_id}']['get']['responses']['200']['content']['application/json']"
        create_req = f"paths['{base}']['post']['requestBody']['content']['application/json']"
        create_res = f"paths['{base}']['post']['responses'][keyof paths['{base}']['post']['responses']]['content']['application/json']"
        update_req = f"paths['{base_id}']['put']['requestBody']['content']['application/json']"
        update_res = f"paths['{base_id}']['put']['responses'][keyof paths['{base_id}']['put']['responses']]['content']['application/json']"
        delete_res = f"paths['{base_id}']['delete']['responses'][keyof paths['{base_id}']['delete']['responses']]"

        # Emit list/get + item extractor (array element or object)
        emit(ListAlias, list_rhs)
        emit(GetAlias, get_rhs)
        out.append(f"type __{Model}List = {ListAlias};\n")
        out.append(f"export type {ItemAlias} = __{Model}List extends (infer T)[] ? T : __{Model}List;\n")

        # Emit requests/responses
        emit(CreateReq, create_req)
        emit(CreateRes, create_res)
        emit(UpdateReq, update_req)
        emit(UpdateRes, update_res)
        emit(DeleteRes, delete_res)
        out.append("\n")

    # Custom endpoints (non-CRUD)
    for p, methods in paths.items():
        if any(p == base or p.startswith(base) for base in crud_set):
            continue
        segs = path_segments(p)
        literals = [s for s in segs if "{" not in s and "}" not in s]
        leaf = literals[-1] if literals else "op"
        ns = [pascal(x.replace("-", "_")) for x in literals[:-1]]
        base_name = "".join(ns + [pascal(leaf)])

        for m, op in methods.items():
            mu = m.lower()
            if mu not in ("get","post","put","patch","delete"): continue
            resp_code = first_success_code(op)
            if resp_code:
                resp_rhs = f"paths['{p}']['{mu}']['responses']['{resp_code}']"
                # try to index into json content if available
                resp_rhs = f"({resp_rhs} extends {{ content: infer C }} ? (C extends {{ 'application/json': infer J }} ? J : {resp_rhs}) : {resp_rhs})"
                emit(f"{base_name}{pascal(mu)}Response", resp_rhs)
            # body type (if any)
            rb = op.get("requestBody")
            if isinstance(rb, dict) and "content" in rb:
                emit(f"{base_name}{pascal(mu)}Request",
                     f"paths['{p}']['{mu}']['requestBody']['content']['application/json']")
        out.append("\n")

    return "".join(out)

# ----------------- client.ts -----------------

CLIENT_TS = """// Tiny typed client factory for openapi-fetch
import createClient from 'openapi-fetch';
import type { paths } from './openapi';

export function makeClient(baseUrl: string, defaults?: RequestInit) {
  return createClient<paths>({
    baseUrl,
    fetch: (input: RequestInfo | URL, init?: RequestInit) =>
      fetch(input, {
        ...defaults,
        ...init,
        headers: {
          ...(defaults?.headers ?? {}),
          ...(init?.headers ?? {}),
        },
      }),
  });
}
"""

# ----------------- main -----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True, help="Import path to FastAPI app instance or a factory (module:symbol)")
    ap.add_argument("--out", required=True, help="Frontend output dir, e.g. ../frontend/src/wapp")
    ap.add_argument("--overwrite-client", action="store_true")
    ap.add_argument("--openapi-typescript", default="npx openapi-typescript")
    ap.add_argument("--emit-openapi-ts", action="store_true", help="Emit openapi.ts instead of .ts (recommended)")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out).resolve()
    ensure_dir(out_dir)

    sym = import_symbol(args.app)
    try:
        from fastapi import FastAPI
    except Exception:
        FastAPI = None

    app = None
    if FastAPI is not None and isinstance(sym, FastAPI):
        app = sym
    elif inspect.isfunction(sym):
        app = sym()
    elif hasattr(sym, "openapi") and hasattr(sym, "router"):
        app = sym
    elif inspect.isclass(sym):
        try:
            app = sym()
        except TypeError:
            pass

    if app is None or not hasattr(app, "openapi"):
        raise SystemExit("`--app` must be a FastAPI instance (e.g. 'main:app') or a zero-arg factory (e.g. 'main:create_app').")

    spec = app.openapi()

    # 1) openapi.json
    openapi_json = out_dir / "openapi.json"
    write_text(openapi_json, json.dumps(spec, ensure_ascii=False, indent=2))
    print(f"✅ Wrote {openapi_json}")

    # 2) openapi types
    if args.emit_openapi_ts:
        openapi_types = out_dir / "openapi.ts"
    else:
        openapi_types = out_dir / "openapi.ts"
    cmd = f'{args.openapi_typescript} "{openapi_json}" -o "{openapi_types}"'
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        raise SystemExit("openapi-typescript failed. Is Node/npm available?")
    print(f"✅ Wrote {openapi_types}")

    # 3) client.ts
    client_ts = out_dir / "client.ts"
    if args.overwrite_client or not client_ts.exists():
        write_text(client_ts, CLIENT_TS)
        print(f"✅ Wrote {client_ts} {'(overwritten)' if args.overwrite_client else ''}")

    # 4) api.ts
    api_ts = out_dir / "api.ts"
    write_text(api_ts, build_facade(spec))
    print(f"✅ Wrote {api_ts}")

    # 5) models.ts (request/response aliases + inferred Item types)
    models_ts = out_dir / "models.ts"
    write_text(models_ts, build_models(spec))
    print(f"✅ Wrote {models_ts}")

    print("✅✅✅ Done.")

if __name__ == "__main__":
    main()
