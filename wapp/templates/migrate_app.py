# migrate_app.py
from __future__ import annotations
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

# Import your app factory and db
from app import create_app
from app_env import db, DATABASE_URL

BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"  # contains env.py and versions/

def alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg

def ensure_migrations_dir():
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    (MIGRATIONS_DIR / "versions").mkdir(parents=True, exist_ok=True)
    # we ship our own env.py (next step), so we don't call command.init()

def has_diff() -> bool:
    app = create_app(bind=False)
    with app.app_context():
        with db.engine.connect() as conn:
            mc = MigrationContext.configure(conn)
            diffs = compare_metadata(mc, db.metadata)
            return bool(diffs)

def autogen_if_needed(cfg: Config, message: str = "autogenerate"):
    def _process_revision_directives(context, revision, directives):
        if not directives:
            return
        script = directives[0]
        if not getattr(script, "upgrade_ops", None) or script.upgrade_ops.is_empty():
            directives[:] = []
            print("No schema changes detected.")
    command.revision(cfg, message=message, autogenerate=True,
                     process_revision_directives=_process_revision_directives)

def main(argv: list[str] | None = None):
    argv = argv or sys.argv[1:]
    cfg = alembic_config()
    ensure_migrations_dir()

    if not argv:
        # smart default: check → create rev if needed → upgrade head
        if has_diff():
            autogen_if_needed(cfg)
        else:
            print("No schema changes; skipping revision.")
        command.upgrade(cfg, "head")
        return

    cmd = argv[0]
    if cmd == "check":
        changed = has_diff()
        print("diff:changed" if changed else "diff:none")
        sys.exit(1 if changed else 0)
    if cmd == "revision":
        autogen_if_needed(cfg)
        return
    if cmd == "upgrade":
        target = argv[1] if len(argv) > 1 else "head"
        command.upgrade(cfg, target); return
    if cmd == "downgrade":
        target = argv[1] if len(argv) > 1 else "-1"
        command.downgrade(cfg, target); return
    if cmd in {"current", "history", "stamp"}:
        args = argv[1:]
        getattr(command, cmd)(cfg, *args); return

    print(f"Unknown command: {cmd}")
    sys.exit(2)

if __name__ == "__main__":
    main()
