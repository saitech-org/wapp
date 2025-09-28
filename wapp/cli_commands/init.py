from __future__ import annotations

import os
import sys
import shutil
import subprocess
from pathlib import Path
from importlib import resources

import click

TEMPLATE_FILES = ["app.py","users_demo.py","settings.py","automigrate.py"]

DEPENDENCIES = [
    "saitech-wapp","fastapi","uvicorn[standard]","sqlalchemy","alembic",
    "pydantic","python-dotenv","aiosqlite",
]

ALEMBIC_DIR = "migrations"
PACKAGE_TEMPLATES = "wapp.templates"


def _env() -> dict:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    return env


def _exe(name: str) -> str | None:
    return shutil.which(name)


def _build_install_cmd(installer: str, deps: list[str]) -> list[str] | None:
    installer = installer.lower()

    if installer == "uv" and _exe("uv"):
        return ["uv", "pip", "install", "--upgrade", *deps]
    if installer == "pip":
        return [sys.executable, "-m", "pip", "install", "--upgrade", *deps]
    if installer == "poetry" and _exe("poetry"):
        return ["poetry", "add", *deps]
    if installer == "pdm" and _exe("pdm"):
        return ["pdm", "add", *deps]
    if installer == "rye" and _exe("rye"):
        return ["rye", "add", *deps]
    if installer == "hatch" and _exe("hatch"):
        return ["hatch", "run", "pip", "install", "--upgrade", *deps]
    if installer == "conda" and _exe("conda"):
        return [sys.executable, "-m", "pip", "install", "--upgrade", *deps]
    if installer == "none":
        return []
    return None


def _auto_detect_installer() -> str:
    cwd = Path.cwd()
    pyproject = cwd / "pyproject.toml"

    def has_text(path: Path, needle: str) -> bool:
        try:
            return needle in path.read_text(encoding="utf-8")
        except Exception:
            return False

    if pyproject.exists():
        if has_text(pyproject, "[tool.poetry]") and _exe("poetry"):
            return "poetry"
        if has_text(pyproject, "[tool.pdm]") and _exe("pdm"):
            return "pdm"
        if has_text(pyproject, "[tool.rye]") and _exe("rye"):
            return "rye"
        if has_text(pyproject, "[tool.hatch]") and _exe("hatch"):
            return "hatch"

    if (cwd / "poetry.lock").exists() and _exe("poetry"):
        return "poetry"
    if (cwd / "pdm.lock").exists() and _exe("pdm"):
        return "pdm"
    if (cwd / "rye.lock").exists() and _exe("rye"):
        return "rye"
    if (cwd / "hatch.toml").exists() and _exe("hatch"):
        return "hatch"

    if _exe("uv"):
        return "uv"
    return "pip"


def _install_deps(installer: str, deps: list[str]) -> None:
    chosen = installer if installer != "auto" else _auto_detect_installer()
    cmd = _build_install_cmd(chosen, deps)

    if cmd is None:
        raise RuntimeError(
            f"Installer '{installer}' not available. "
            "Choose one of: auto, uv, pip, poetry, pdm, rye, hatch, conda, none."
        )

    if cmd == []:
        click.echo("Skipping dependency installation (--installer=none).")
        return

    if chosen == "pip":
        try:
            import pip  # noqa: F401
        except Exception:
            subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True, env=_env())

    subprocess.run(cmd, check=True, env=_env())


def _copy_templates():
    cwd = Path.cwd()
    for filename in TEMPLATE_FILES:
        dest_path = cwd / filename
        if dest_path.exists():
            click.echo(f"Skipping {filename}: already exists.")
            continue
        try:
            with resources.files(PACKAGE_TEMPLATES).joinpath(filename).open("r", encoding="utf-8") as src_file:
                dest_path.write_text(src_file.read(), encoding="utf-8")
            click.echo(f"Created {filename}")
        except Exception as e:
            click.echo(f"Error copying {filename}: {e}")


def _init_alembic():
    cwd = Path.cwd()
    mig_dir = cwd / ALEMBIC_DIR
    if mig_dir.exists():
        click.echo(f"Alembic already initialized at ./{ALEMBIC_DIR}, skipping init.")
        return
    subprocess.run([sys.executable, "-m", "alembic", "init", ALEMBIC_DIR], check=True, env=_env())


def _patch_alembic_env():
    env_path = Path.cwd() / ALEMBIC_DIR / "env.py"
    if not env_path.exists():
        click.echo("Alembic env.py not found; skipping metadata wiring.")
        return
    try:
        with resources.files(PACKAGE_TEMPLATES).joinpath("env.py").open("r", encoding="utf-8") as tmpl:
            env_path.write_text(tmpl.read(), encoding="utf-8")
        click.echo("Wrote migrations/env.py from template.")
    except Exception as e:
        click.echo(f"Error writing migrations/env.py from template: {e}")
        content = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
        already_imported = any("from app_env import db" in ln for ln in content)
        replaced = False
        for i, ln in enumerate(content):
            if "target_metadata = None" in ln:
                if not already_imported:
                    content[i] = "from app_env import db\n\ntarget_metadata = db.metadata\n"
                else:
                    content[i] = "target_metadata = db.metadata\n"
                replaced = True
                break
        if not replaced:
            if not already_imported:
                content.insert(0, "from app_env import db\n")
            if not any("target_metadata" in ln for ln in content):
                content.insert(1, "target_metadata = db.metadata\n")
        env_path.write_text("".join(content), encoding="utf-8")
        click.echo("Patched migrations/env.py target_metadata (fallback).")


# --- click command definition (unchanged) ---

@click.command(name="init")
@click.option(
    "--install-deps/--no-install-deps",
    default=True,
    help="Install required dependencies (default: on).",
)
@click.option(
    "--installer",
    type=click.Choice(["auto", "uv", "pip", "poetry", "pdm", "rye", "hatch", "conda", "none"], case_sensitive=False),
    default="auto",
    help="Which package manager to use for installing deps.",
)
def command(install_deps: bool, installer: str):
    """Bootstrap a new Wapp project in the current directory."""
    try:
        _copy_templates()
        if install_deps:
            _install_deps(installer, DEPENDENCIES)
        else:
            click.echo("Skipping dependency installation (--no-install-deps).")
        _init_alembic()
        _patch_alembic_env()
        click.echo("Wapp project initialized successfully in the current directory!")
    except subprocess.CalledProcessError as cpe:
        click.echo(f"Error initializing project (command failed): {cpe}")
        raise SystemExit(cpe.returncode)
    except Exception as e:
        click.echo(f"Error initializing project: {e}")
        raise SystemExit(1)
