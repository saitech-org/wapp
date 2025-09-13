"""
Manual migration script for Alembic.

Usage:
    python -m wapp.migrate
    # or, if installed as a CLI:
    wapp-migrate

- In production: Call this script from your Docker entrypoint or manually before starting the app.
- In development: You may run this script as needed, or automate it if desired.

IMPORTANT:
    For Alembic autogenerate to detect your models, you must import your SQLAlchemy db instance (e.g., from env import db) in your migrations/env.py and set:
        target_metadata = db.metadata
    This ensures Alembic uses the same metadata as your app.

This script will:
  1. Autogenerate a migration if there are model changes (no-op if no changes).
  2. Apply all migrations to bring the database schema up to date.
"""
import os
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext

DATABASE_URL = os.getenv('DATABASE_URL')
WAPP_ALEMBIC_INI = os.getenv('WAPP_ALEMBIC_INI', 'alembic.ini')

def has_pending_changes():
    """Return True if there are model changes not yet reflected in the DB."""
    alembic_cfg = Config(WAPP_ALEMBIC_INI)
    script = ScriptDirectory.from_config(alembic_cfg)
    def _check_for_changes(rev, context):
        diff = context._compare_metadata(context.connection, context.opts['target_metadata'])
        return bool(diff)
    with EnvironmentContext(alembic_cfg, script, as_sql=False, fn=_check_for_changes) as env:
        with env.get_context().connection.begin():
            return env.run_migrations()

def main():
    alembic_cfg = Config(WAPP_ALEMBIC_INI)

    # Ensure the migrations directory exists
    script_location = alembic_cfg.get_main_option('script_location')
    ini_dir = os.path.dirname(os.path.abspath(WAPP_ALEMBIC_INI))
    migrations_dir = os.path.abspath(os.path.join(ini_dir, script_location))
    if not os.path.exists(migrations_dir):
        os.makedirs(migrations_dir)
    env_py = os.path.join(migrations_dir, 'env.py')
    if not os.path.exists(env_py):
        # Initialize Alembic environment if missing
        print(f"[migrate.py] Alembic env.py not found, initializing Alembic environment in {migrations_dir}...")
        import subprocess
        subprocess.run(['alembic', 'init', migrations_dir], check=True)

    if DATABASE_URL:
        alembic_cfg.set_main_option('sqlalchemy.url', DATABASE_URL)
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
