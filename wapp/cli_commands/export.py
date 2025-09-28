import os
import sys
import subprocess
from pathlib import Path

import click


def _env() -> dict:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    return env


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


@click.command(name="export")
@click.option("--app", required=True, help="Import path to FastAPI app instance or factory (module:symbol)")
@click.option("--out", required=True, help="Frontend output dir, e.g. ../frontend/src/wapp")
@click.option("--overwrite-client", is_flag=True, help="Overwrite the generated client.ts if present")
@click.option("--openapi-typescript", default="npx openapi-typescript", help="Command to run openapi-typescript (default: npx openapi-typescript)")
@click.option("--emit-openapi-ts", is_flag=True, help="Emit openapi.ts instead of .ts (recommended)")
def command(app: str, out: str, overwrite_client: bool, openapi_typescript: str, emit_openapi_ts: bool):
    """Export OpenAPI JSON and TypeScript artifacts using the bundled exporter."""
    out_dir = Path(out).resolve()
    ensure_dir(out_dir)

    cmd = [sys.executable, "-m", "wapp.tools.export_openapi_ts", "--app", app, "--out", str(out_dir)]
    if overwrite_client:
        cmd.append("--overwrite-client")
    if openapi_typescript:
        cmd.extend(["--openapi-typescript", openapi_typescript])
    if emit_openapi_ts:
        cmd.append("--emit-openapi-ts")

    try:
        res = subprocess.run(cmd, check=False, env=_env())
        if res.returncode != 0:
            click.echo("Export failed (see errors above).")
            raise SystemExit(res.returncode)
        click.echo(f"OpenAPI artifacts written to {out_dir}")
    except FileNotFoundError as e:
        click.echo(f"Failed to run exporter: {e}")
        raise SystemExit(1)

