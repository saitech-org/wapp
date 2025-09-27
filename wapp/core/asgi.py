# wapp/core/asgi.py
import inspect
import re
from typing import Any, Dict, List, Optional, Tuple, Type

from fastapi import FastAPI, Request, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel as PydanticModel, create_model
from sqlalchemy import Column
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from starlette.middleware.cors import CORSMiddleware

_PARAM_RE = re.compile(r"\{(?P<name>[a-zA-Z_]\w*)(?::(?P<type>int|str|float))?}")

_TYPE_MAP = {
    None: str,
    "str": str,
    "int": int,
    "float": float,
}

def _parse_path_params(fastapi_path: str):
    # returns a list of (name, py_type)
    out = []
    for m in _PARAM_RE.finditer(fastapi_path):
        name = m.group("name")
        typ = _TYPE_MAP[m.group("type")]
        out.append((name, typ))
    return out



class BaseModel(DeclarativeBase):
    ...


# ---------- DB bootstrap (async) ----------

def make_sessionmaker(db_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(db_url, future=True, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)

async def get_session(session_maker: async_sessionmaker[AsyncSession]):
    async with session_maker() as s:
        yield s

# ---------- Minimal endpoint contract (class-based, FastAPI-ready) ----------


def _humanize_tag(name: str) -> str:
    return name.replace("_", " ").strip().title() or "Default"

class EndpointMeta(PydanticModel):
    method: str
    pattern: str
    name: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    request_model: Optional[Type[PydanticModel]] = None
    response_model: Optional[Type[PydanticModel]] = None
    tags: List[str] = []

class WappEndpoint:
    Meta: EndpointMeta  # just a type hint for editors

    async def handle(self, request: Request, query: Dict[str, Any], path: Dict[str, Any], body: Any, session: AsyncSession):
        raise NotImplementedError

# ---------- Utilities ----------

_path_int   = re.compile(r"<int:([a-zA-Z_]\w*)>")
_path_str   = re.compile(r"<string:([a-zA-Z_]\w*)>")
_path_plain = re.compile(r"<([a-zA-Z_]\w*)>")

def flask_to_fastapi_path(p: str) -> str:
    p = _path_int.sub(r"{\1:int}", p)
    p = _path_str.sub(r"{\1:str}", p)
    p = _path_plain.sub(r"{\1}", p)
    return p

def _col_is_autoincrement(col: Column) -> bool:
    return bool(col.autoincrement or (col.primary_key and col.type.python_type in (int,)))

def _pyd_name(model: PydanticModel) -> str:
    return f"{model.__name__}"

# ---------- Pydantic schema autogen (from SQLAlchemy Model) ----------

def build_pyd_from_sqla(
    sa_model: Type[PydanticModel],
    *,
    mode: str,   # "out" | "create" | "update"
) -> Type[PydanticModel]:
    """
    Generate Pydantic models directly from SQLAlchemy columns.
    - out: includes PK + all columns (readonly feel)
    - create: all non-nullable, non-PK (PK only if not autoincrement)
    - update: all optional (partial)
    """
    fields: Dict[str, Tuple[Any, Any]] = {}
    for col in sa_model.__table__.columns:  # type: ignore[attr-defined]
        py_t = getattr(col.type, "python_type", str)  # fallback
        required = not col.nullable and col.default is None and col.server_default is None

        if mode == "out":
            default = ... if required and not _col_is_autoincrement(col) else None
            fields[col.name] = (py_t, default if default is not None else None)

        elif mode == "create":
            if col.primary_key and _col_is_autoincrement(col):
                continue  # let DB generate
            # require if needed
            default = ... if required and not col.primary_key else None
            fields[col.name] = (py_t, default if default is not None else None)

        elif mode == "update":
            # all optional
            fields[col.name] = (Optional[py_t], None)

    model_name = f"{_pyd_name(sa_model)}_{mode.capitalize()}"
    return create_model(model_name, **fields)  # type: ignore

# ---------- Auto-CRUD router (async SQLAlchemy 2.x) ----------
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

def _finalize_dyn_model(m):
    # Give Pydantic v2 a stable identity and ensure it’s built
    m.__module__ = "wapp.autogen"
    if hasattr(m, "model_rebuild"):
        m.model_rebuild()
    return m

def make_crud_router(sa_model, *, session_dep, slug: str, group_tag: str) -> APIRouter:
    Out    = _finalize_dyn_model(build_pyd_from_sqla(sa_model, mode="out"))
    Create = _finalize_dyn_model(build_pyd_from_sqla(sa_model, mode="create"))
    Update = _finalize_dyn_model(build_pyd_from_sqla(sa_model, mode="update"))

    r = APIRouter(prefix=f"/{slug}", tags=[group_tag])

    # --- list ---
    async def list_handler(page: int = 1, page_size: int = 50,
                           session: AsyncSession = Depends(session_dep)):
        stmt = select(sa_model).offset((page - 1) * page_size).limit(page_size)
        rows = (await session.execute(stmt)).scalars().all()
        return [Out.model_validate(obj, from_attributes=True) for obj in rows]
    r.get("/", response_model=list[Out])(list_handler)  # Python 3.9+: use List[Out]

    # --- get_one ---
    async def get_handler(id: int, session: AsyncSession = Depends(session_dep)):
        obj = await session.get(sa_model, id)
        if not obj:
            raise HTTPException(404, "Not found")
        return Out.model_validate(obj, from_attributes=True)
    r.get("/{id:int}", response_model=Out)(get_handler)

    # --- create ---
    async def create_handler(payload: Create = Body(...),
                             session: AsyncSession = Depends(session_dep)):
        obj = sa_model(**payload.model_dump())
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return Out.model_validate(obj, from_attributes=True)
    r.post("/", response_model=Out, status_code=201)(create_handler)

    # --- update ---
    async def update_handler(id: int, payload: Update = Body(...),
                             session: AsyncSession = Depends(session_dep)):
        obj = await session.get(sa_model, id)
        if not obj:
            raise HTTPException(404, "Not found")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        await session.commit()
        await session.refresh(obj)
        return Out.model_validate(obj, from_attributes=True)
    r.put("/{id:int}", response_model=Out)(update_handler)

    # --- delete ---
    async def delete_handler(id: int, session: AsyncSession = Depends(session_dep)):
        obj = await session.get(sa_model, id)
        if obj:
            await session.delete(obj)
            await session.commit()
        return {}
    r.delete("/{id:int}", status_code=204)(delete_handler)

    return r


# ---------- Wapp (ASGI edition) ----------

class Wapp:
    """
    Keep the exact ergonomics:
      class Example(Wapp):
          class Models:
              some_entity = SomeEntity
          class Endpoints:
              _some_entity = True            # auto CRUD
              get_by_name = GetByName        # custom endpoint class
          class Wapps:
              nested = OtherWapp
    """
    class Models: ...
    class Endpoints: ...
    class Wapps: ...

    @classmethod
    def get_models(cls) -> List[Tuple[str, Type[PydanticModel]]]:
        models = getattr(cls, "Models", None)
        if not models:
            return []
        out = []
        for name, obj in models.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, BaseModel) and name[0] != "_":
                out.append((name, obj))
        return out

    @classmethod
    def get_wapps(cls) -> List[Tuple[str, Type["Wapp"]]]:
        wapps = getattr(cls, "Wapps", None)
        if not wapps:
            return []
        out = []
        for name, obj in wapps.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, Wapp) and obj is not cls:
                out.append((name, obj))
        return out

    @classmethod
    def get_endpoints(cls) -> List[Tuple[str, Type[WappEndpoint]]]:
        eps = getattr(cls, "Endpoints", None)
        if not eps:
            return []
        out = []
        for name, obj in eps.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, WappEndpoint):
                out.append((name, obj))
        return out

    @classmethod
    def build_router(cls, *, session_dep, prefix: str = "", group_tag: str = None) -> APIRouter:
        # make the router carry the group tag; we’ll still set per-route tags explicitly
        router = APIRouter(prefix=prefix)

        # 1) Auto CRUD (use the wapp's group_tag, not model names)
        model_map = {n: m for n, m in cls.get_models()}
        eps_container = getattr(cls, "Endpoints", None)
        if eps_container:
            for attr_name, val in eps_container.__dict__.items():
                if not attr_name.startswith("_"):
                    continue
                model_name = attr_name[1:]
                model = model_map.get(model_name)
                if not model:
                    continue
                meta = getattr(model, "Meta", None)
                if not meta or not getattr(meta, "slug", None):
                    raise ValueError(f"Model '{model_name}' missing Meta.slug")
                slug = meta.slug

                if val is True or isinstance(val, dict):
                    crud_router = make_crud_router(
                        model,
                        session_dep=session_dep,
                        slug=slug,
                        group_tag=group_tag,  # <- enforce single tag
                    )
                    router.include_router(crud_router)

        # 2) Custom endpoints (force this wapp’s group_tag)
        for _, ep_cls in cls.get_endpoints():
            meta: EndpointMeta = getattr(ep_cls, "Meta", None)
            if not meta or not meta.method or not meta.pattern:
                continue

            fpath = flask_to_fastapi_path(meta.pattern)
            method = meta.method.upper()
            path_params_spec = _parse_path_params(fpath)

            # create the handler (real function still accepts **path_kwargs)
            def _create_handler(ep_cls=ep_cls, meta=meta, path_params_spec=path_params_spec):
                async def handler(
                        request: Request,
                        session: AsyncSession = Depends(session_dep),
                        **path_kwargs,
                ):
                    body = None
                    if request.method in ("POST", "PUT", "PATCH"):
                        try:
                            raw = await request.json()
                        except Exception:
                            raw = None
                        body = meta.request_model.model_validate(raw) if meta.request_model and raw is not None else raw

                    inst = ep_cls()
                    result = await inst.handle(request, dict(request.query_params), path_kwargs, body, session)
                    if isinstance(result, tuple) and len(result) == 2:
                        payload, status = result
                        return JSONResponse(payload, status_code=status)
                    return result

                # ---- IMPORTANT: publish a signature WITHOUT **path_kwargs ----
                params = [
                    inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
                ]
                for name, typ in path_params_spec:
                    params.append(
                        inspect.Parameter(
                            name=name,
                            kind=inspect.Parameter.KEYWORD_ONLY,
                            annotation=typ,
                            default=Path(...),
                        )
                    )
                params.append(
                    inspect.Parameter(
                        "session",
                        inspect.Parameter.KEYWORD_ONLY,
                        annotation=AsyncSession,
                        default=Depends(session_dep),
                    )
                )
                handler.__signature__ = inspect.Signature(parameters=params)  # <- no VAR_KEYWORD here
                return handler

            handler = _create_handler()

            kwargs = dict(
                path=fpath,
                name=meta.name or ep_cls.__name__,
                summary=meta.summary,
                description=meta.description,
                response_model=meta.response_model,
                tags=[group_tag],
            )
            if method == "GET":
                router.get(**kwargs)(handler)
            elif method == "POST":
                router.post(**kwargs)(handler)
            elif method == "PUT":
                router.put(**kwargs)(handler)
            elif method == "PATCH":
                router.patch(**kwargs)(handler)
            elif method == "DELETE":
                router.delete(**kwargs)(handler)
            else:
                raise ValueError(f"Unsupported method: {method}")

        # 3) Nested wapps: derive child tag from attribute name
        for wname, wcls in cls.get_wapps():
            child_tag = _humanize_tag(wname)
            child = wcls.build_router(
                session_dep=session_dep,
                prefix=f"/{wname}",
                group_tag=child_tag,
            )
            router.include_router(child)

        return router

# ---------- Factory for an app with a root Wapp ----------

def make_sessionmaker(db_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(db_url, future=True, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)

def get_session_dep(session_maker: async_sessionmaker[AsyncSession]):
    # returns a FastAPI dependency function
    async def _dep():
        async with session_maker() as s:
            yield s
    return _dep

def make_app(root_wapp: Type[Wapp], *, db_url: str, title: str = "Wapp API", lifespan=None) -> FastAPI:
    session_maker = make_sessionmaker(db_url)

    session_dep = get_session_dep(session_maker)

    app = FastAPI(title=title, lifespan=lifespan)
    app.include_router(root_wapp.build_router(session_dep=session_dep))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app
