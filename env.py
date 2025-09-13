import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables from .env if present

load_dotenv()

ENV = os.getenv('ENV', 'development')

WAPP_ALEMBIC_INI = os.getenv('WAPP_ALEMBIC_INI', os.path.join(os.path.dirname(__file__), 'alembic.ini'))
WAPP_ALEMBIC_MIGRATIONS_DIR = os.getenv('WAPP_ALEMBIC_MIGRATIONS_DIR', os.path.join(os.path.dirname(__file__), 'migrations'))
WAPP_AUTO_MIGRATE = os.getenv('AUTO_MIGRATE', 'true').lower() == 'true'

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')

db = SQLAlchemy()
