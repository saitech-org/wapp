import os
import click


@click.command()
@click.argument('project_name')
def wapp_init(project_name):
    """Bootstrap a new Wapp project."""
    os.makedirs(project_name)
    files_to_create = {
        'app.py': '''import subprocess
import sys
from app_env import ENV
from create_app import create_app

if __name__ == '__main__':
    if ENV == 'development':
        subprocess.run([sys.executable, "-m", "migrate_app"], check=True)
    app = create_app(bind=True)
    app.run(debug=True)
''',
        'app_env.py': '''import os
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()
ENV = os.getenv("ENV", "development")
db = SQLAlchemy()
BASE_DIR = Path(__file__).resolve().parent
def normalize_sqlite_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        rel = url[len("sqlite:///"):]
        db_path = (BASE_DIR / rel).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return "sqlite:///" + db_path.as_posix()
    return url
RAW_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///instance/app.db")
DATABASE_URL = normalize_sqlite_url(RAW_DATABASE_URL)
print(DATABASE_URL)
''',
        'migrate_app.py': '''from __future__ import annotations
import sys
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app import create_app
from app_env import db, DATABASE_URL

BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"
def alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg
''',
    }
    for filename, content in files_to_create.items():
        try:
            with open(os.path.join(project_name, filename), 'w') as f:
                f.write(content)
        except Exception as e:
            click.echo(f'Error initializing project: {e}')

    click.echo(f'Project {project_name} initialized successfully!')


if __name__ == '__main__':
    wapp_init()
