# automigrate.py — lifespan helper used by the demo app to run alembic autogenerate on startup
# This file will be copied to the user's project by wapp-init and mirrors the project's automigrate.py
import os
import sys
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager


def _run(cmd: list[str], *, cwd: Path, env: dict):
    completed = subprocess.run(cmd, check=True, cwd=str(cwd), env=env)
    return completed.returncode


@asynccontextmanager
async def lifespan_with_subprocess(app):
    if os.getenv("AUTO_MIGRATE", "1") in ("0", "false", "False"):
        yield
        return

    root = Path(__file__).resolve().parents[0]
    ini = root / "alembic.ini"
    if not ini.exists():
        raise RuntimeError(f"alembic.ini not found at: {ini}")

    env = os.environ.copy()

    print("Running migrations (upgrade → autogenerate → upgrade)...")
    print(f"- CWD: {root}")
    print(f"- INI: {ini}")

    # 1) Ensure DB is at head
    print("Applying any pending migrations (upgrade head)...")
    _run([sys.executable, "-m", "alembic", "-c", str(ini), "upgrade", "head"], cwd=root, env=env)

    # 2) Try to create a new revision with autogenerate
    print("Generating new migration (revision --autogenerate)...")
    try:
        _run([sys.executable, "-m", "alembic", "-c", str(ini), "revision", "--autogenerate", "-m", "auto"], cwd=root, env=env)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "Alembic autogenerate failed. Make sure your env.py allows revision creation when DB is at head"
        ) from e

    # 3) Apply any newly generated revision
    print("Applying any new migrations (upgrade head)...")
    _run([sys.executable, "-m", "alembic", "-c", str(ini), "upgrade", "head"], cwd=root, env=env)

    # 4) Optional: auto-export OpenAPI TypeScript artifacts
    if os.getenv("AUTO_EXPORT", "1") not in ("0", "false", "False"):
        try:
            out_dir = root / "frontend" / "src" / "wapp"
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"Running OpenAPI export to: {out_dir}")
            cmd = [
                sys.executable,
                "-m",
                "wapp.tools.export_openapi_ts",
                "--app",
                "app:app",
                "--out",
                str(out_dir),
            ]
            # Run exporter but don't raise on failure so startup isn't blocked
            res = subprocess.run(cmd, check=False, cwd=str(root), env=env)
            if res.returncode != 0:
                print(f"OpenAPI export failed (exit {res.returncode}). You can run: {' '.join(cmd)}")
            else:
                print("OpenAPI artifacts generated successfully.")
        except FileNotFoundError as e:
            print(f"Failed to run exporter: {e}. Ensure the exporter module is available.")
        except Exception as e:
            print(f"OpenAPI export error: {e}")

    yield
