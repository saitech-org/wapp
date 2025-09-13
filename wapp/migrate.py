# wapp/migrate.py
from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app import create_app
from app_env import db, DATABASE_URL

HERE = Path(__file__).resolve().parent
MIGRATIONS_DIR = HERE / "migrations"  # contains env.py and versions/

def _alembic_config() -> Config:
    cfg = Config()  # no alembic.ini needed; we set options here
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    # Optional niceties
    cfg.set_main_option("timezone", "utc")
    return cfg

def _ensure_migrations_dir(cfg: Config):
    """Initialize 'migrations' folder if it doesn't exist."""
    if not MIGRATIONS_DIR.exists():
        # Create parent and init Alembic skeleton (env.py we already provide)
        MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
        (MIGRATIONS_DIR / "versions").mkdir(exist_ok=True)
        # We DO NOT call command.init because we ship our own env.py.

def _has_metadata_diff() -> bool:
    """Return True if there are model vs DB schema differences."""
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            mc = MigrationContext.configure(conn)
            diffs = compare_metadata(mc, db.metadata)
            return bool(diffs)

def _autogenerate_revision_if_needed(cfg: Config, message: str = "autogenerate"):
    """
    Create a revision only if autogenerate finds real changes.
    Uses a callback to cancel creating empty migrations.
    """
    def _process_revision_directives(context, revision, directives):
        # If Alembic found nothing, prevent creating an empty file.
        if directives:
            script = directives[0]
            if not getattr(script, "upgrade_ops", None):
                directives[:] = []
                print("No schema changes detected (no upgrade_ops).")
                return
            if script.upgrade_ops.is_empty():
                directives[:] = []
                print("No schema changes detected.")
                return

    command.revision(
        cfg,
        message=message,
        autogenerate=True,
        process_revision_directives=_process_revision_directives,
    )

def main(argv: list[str] | None = None):
    """
    Usage:
      python -m wapp.migrate           # check, create revision if needed, then upgrade
      python -m wapp.migrate check     # just check for diffs (exit 0/1)
      python -m wapp.migrate revision  # force a revision if there are changes
      python -m wapp.migrate upgrade   # upgrade to head
      python -m wapp.migrate downgrade -1  # example passthrough
    """
    argv = argv or sys.argv[1:]
    cfg = _alembic_config()
    _ensure_migrations_dir(cfg)

    # Ensure app context for db.engine usage inside env.py runs
    app = create_app()
    with app.app_context():
        if not argv:
            # default: smart pipeline (check → revision if needed → upgrade)
            if _has_metadata_diff():
                _autogenerate_revision_if_needed(cfg)
            else:
                print("No schema changes detected; skipping revision.")
            command.upgrade(cfg, "head")
            return

        cmd = argv[0]

        if cmd == "check":
            changed = _has_metadata_diff()
            print("diff:changed" if changed else "diff:none")
            sys.exit(0 if not changed else 1)

        if cmd == "revision":
            _autogenerate_revision_if_needed(cfg)
            return

        if cmd == "upgrade":
            target = argv[1] if len(argv) > 1 else "head"
            command.upgrade(cfg, target)
            return

        if cmd == "downgrade":
            target = argv[1] if len(argv) > 1 else "-1"
            command.downgrade(cfg, target)
            return

        # pass-through for other alembic commands if you want:
        # e.g. "current", "history", etc.
        if cmd in {"current", "history", "stamp"}:
            args = argv[1:] if len(argv) > 1 else []
            getattr(command, cmd)(cfg, *args)
            return

        print(f"Unknown command: {cmd}")
        sys.exit(2)


if __name__ == "__main__":
    main()
