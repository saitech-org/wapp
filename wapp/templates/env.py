# Alembic env.py template tailored for projects where demo.py defines models and DB URL.
# This file will be written into migrations/env.py by the wapp-init command.

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# Import your metadata and optional sync URL from the project's settings module
# settings.py should export DB_URL_SYNC (sync URL string) and models should inherit from wapp.core.asgi.BaseModel
import settings
from wapp.core.asgi import BaseModel

# this is the Alembic Config object, which provides access to values within the .ini file
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the project's metadata for autogeneration
target_metadata = BaseModel.metadata


def get_url() -> str:
    # Prefer an explicit sync URL exported by users' settings; fall back to config
    url = getattr(settings, "DB_URL_SYNC", "")
    if url:
        return url
    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url:
        return ini_url
    raise RuntimeError("No database URL. Set DB_URL_SYNC in demo.py or sqlalchemy.url in alembic.ini")


def process_revision_directives(context, revision, directives):
    # If autogenerate found nothing, prevent creating an empty file.
    if directives and getattr(directives[0], "upgrade_ops", None):
        if directives[0].upgrade_ops.is_empty():
            directives[:] = []
            print("No schema changes detected; skipping revision.")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        process_revision_directives=process_revision_directives,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()

    # If URL is async, use AsyncEngine path; else use sync engine.
    if url.startswith("postgresql+asyncpg"):
        connectable = create_async_engine(url, poolclass=pool.NullPool, future=True)

        async def do_run() -> None:
            async with connectable.connect() as connection:
                await connection.run_sync(
                    lambda sync_conn: context.configure(
                        connection=sync_conn,
                        target_metadata=target_metadata,
                        compare_type=True,
                        compare_server_default=True,
                    )
                )
                await connection.run_sync(lambda _: context.begin_transaction())
                await connection.run_sync(lambda _: context.run_migrations())

        import asyncio
        asyncio.run(do_run())
    else:
        connectable = engine_from_config(
            {"sqlalchemy.url": url},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
        with connectable.connect() as connection:  # type: Connection
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                process_revision_directives=process_revision_directives,
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
