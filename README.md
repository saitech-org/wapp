# Wapp — Quickstart Guide

Wapp is a modular framework for building ASGI APIs (FastAPI-style) with automatic CRUD endpoints, nested applications, Alembic migrations, and optional OpenAPI → TypeScript frontend exports. This guide shows how to bootstrap a project with wapp-init, run the app, manage migrations, and generate TypeScript client artifacts.

---

## Quick Setup

TL;DR

```bash
mkdir my_project && cd my_project
pip install saitech-wapp
wapp-init
python app.py
```

The demo app created by wapp-init exposes API docs at /docs (Swagger UI) and /redoc (ReDoc) by default.

---

## Requirements

* Python 3.8+
* Install the package:

```bash
pip install saitech-wapp
```

If you prefer a project manager, add the package with Poetry / PDM / etc.

---

## Bootstrap a new project

Run the CLI to create a ready-to-run demo project in the current directory:

```bash
wapp-init
```

What wapp-init does:

- Writes a minimal app entrypoint (app.py), demo Wapp (users_demo.py), settings.py and automigrate.py from templates.
- Initializes Alembic migrations (migrations/)
- Optionally installs Python dependencies (pip/poetry/pdm/uv/rye/hatch/etc.)
- Patches migrations/env.py to wire your project's metadata for autogeneration

---

## Run the application

Start the app with the generated entrypoint:

```bash
python app.py
```

The app uses an ASGI server (uvicorn) and exposes automatic API docs at /docs. The bundled automigrate lifespan helper runs during startup and will:

- apply any pending Alembic migrations,
- attempt to autogenerate a new revision and apply it,
- optionally run the OpenAPI → TypeScript exporter (see below).

Control startup behavior with environment variables:

- AUTO_MIGRATE (default 1) — set to 0 or false to skip automigrations
- AUTO_EXPORT (default 1) — set to 0 or false to skip the automatic OpenAPI TypeScript export

---

## Database migrations

Alembic is used for schema migrations. The templates expect two URLs in settings.py:

- DB_URL_ASYNC — async DB URL used by the app (default sqlite+aiosqlite:///./dev.db)
- DB_URL_SYNC — sync DB URL used by Alembic autogenerate (default sqlite:///./dev.db)

Typical manual workflow when you want to create a new baseline manually:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

The automigrate helper (automigrate.py) automatically runs these steps on startup when AUTO_MIGRATE is enabled.

---

## Generating TypeScript artifacts from OpenAPI

Wapp ships with an exporter to write OpenAPI JSON and TypeScript client types for frontend use. The CLI command is:

```bash
wapp export --app app:app --out frontend/src/wapp
```

By default the exporter will try to run a tool such as `npx openapi-typescript` to convert the OpenAPI JSON to idiomatic TypeScript. That external tool (Node.js + npx/npm) may be required if you ask the exporter to emit typed client files.

Options of interest:

- --overwrite-client to overwrite existing client.ts
- --openapi-typescript "npx openapi-typescript" to customize the conversion command
- --emit-openapi-ts to emit openapi.ts instead of openapi.json

The demo project's automigrate helper will run this exporter automatically at startup when AUTO_EXPORT is enabled.

---

## Project structure and examples

The templates use modern SQLAlchemy 2.0 style declarative models and async DB sessions. The demo (users_demo.py) shows:

- Declarative models that inherit from wapp.core.asgi.BaseModel
- Pydantic request/response models for validation and docs
- Async endpoint handlers that receive an AsyncSession
- A Wapp subclass that wires models and endpoints together

A minimal model example (see templates/users_demo.py) uses mapped_column and BaseModel-compatible metadata. Endpoints attach Pydantic request/response models in their Meta configuration so generated OpenAPI docs include types.

---

## Advanced notes

- The init command will attempt to detect and use your preferred installer (poetry, pdm, uv, pip, etc.). Use --installer to override.
- If you want to skip installing dependencies during init, run wapp-init --no-install-deps.
- Automatic exporter requires the exporter module (bundled) and may invoke external Node tooling; export failures are logged and do not block app startup by default.

---

## Conclusion

Wapp helps you scaffold an ASGI API quickly with automatic CRUD, alembic wiring, and optional frontend type generation. Initialize with wapp-init, tweak models and endpoints in the generated files, and use the automigrate+export lifecycle to keep DB schema and client types in sync.

Happy coding 🚀
