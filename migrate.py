"""
Manual migration script for Alembic.

Usage:
    python migrate.py

- In production: Call this script from your Docker entrypoint or manually before starting the app.
- In development: You may run this script as needed, or automate it if desired.

This script will:
  1. Autogenerate a migration if there are model changes (no-op if no changes).
  2. Apply all migrations to bring the database schema up to date.
"""
import os
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from alembic.runtime.migration import MigrationContext

ALEMBIC_INI = os.path.join(os.path.dirname(__file__), 'alembic.ini')
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')

def has_pending_changes():
    """Return True if there are model changes not yet reflected in the DB."""
    alembic_cfg = Config(ALEMBIC_INI)
    script = ScriptDirectory.from_config(alembic_cfg)
    def _check_for_changes(rev, context):
        diff = context._compare_metadata(context.connection, context.opts['target_metadata'])
        return bool(diff)
    with EnvironmentContext(alembic_cfg, script, as_sql=False, fn=_check_for_changes) as env:
        with env.get_context().connection.begin():
            return env.run_migrations()

def main():
    alembic_cfg = Config(ALEMBIC_INI)
    print("[migrate.py] Checking for model changes...")
    # Try to autogenerate a migration if there are changes
    try:
        command.revision(alembic_cfg, message="Auto migration", autogenerate=True)
        print("[migrate.py] Migration file generated (if there were changes).")
    except Exception as e:
        print(f"[migrate.py] No migration generated: {e}")
    print("[migrate.py] Applying migrations...")
    command.upgrade(alembic_cfg, "head")
    print("[migrate.py] Database schema is up to date.")

if __name__ == "__main__":
    main()

