# settings.py - template for DB URLs and other simple configuration
# Copied into new projects by wapp-init. Override via environment variables as needed.
from os import getenv

# Async DB URL used by the app (default: local sqlite aiosqlite file)
DB_URL_ASYNC = getenv("DB_URL_ASYNC", "sqlite+aiosqlite:///./dev.db")

# Sync DB URL used by Alembic (default: local sqlite file for autogenerate)
DB_URL_SYNC = getenv("DB_URL_SYNC", "sqlite:///./dev.db")

# NOTE: For production, set DB_URL_ASYNC to a proper async driver (eg. postgresql+asyncpg://...)
# and DB_URL_SYNC to the corresponding sync driver (eg. postgresql+psycopg://...).

