# Wapp Framework — README (Quickstart + Progressive Tutorial)

Wapp is a modular, plug-and-play framework for building Flask APIs with **automatic CRUD endpoints**, **nested wapps**, and **Alembic migrations**—with optional Swagger UI docs.

This guide takes you from zero to a multi-wapp API in 5 staged steps:

1. **Bootstrap**, 2) **Basic example**, 3) **Nested stats wapp**, 4) **Add Meetings wapp**, 5) **Conditional endpoints by `ENV_APP_TYPE`**.

---

## 0) Prerequisites & Install

```bash
pip install saitech-wapp flask flask_sqlalchemy alembic flasgger python-dotenv pydantic
```

> If you’re on Windows + SQLite, keep paths absolute (we’ll normalize below).

---

## 1) Bootstrap

Create a project:

```
myproject/
  app.py
  app_env.py
  app_factory.py
  migrate_app.py
  migrations/
    env.py
    versions/
  .env
```

### 1.1 `app_env.py` (DB + env setup, robust SQLite path)

```python
# app_env.py
import os
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

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

ENV = os.getenv("ENV", "development")
ENV_APP_TYPE = os.getenv("ENV_APP_TYPE", "manager")  # "manager" | "public"
```

### 1.2 `app_factory.py` (create Flask app, bind wapps, enable Swagger)

```python
# app_factory.py
from flask import Flask
from flasgger import Swagger
from app_env import db, DATABASE_URL, ENV_APP_TYPE
from wapp.core import Wapp

# --- Define your wapps in later stages; keep this scaffold now ---

class MyWapp(Wapp):
    """Root container wapp. We'll add child wapps in later stages."""
    class Wapps:
        pass

def create_app(*, bind: bool = True):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

    import os
    os.makedirs("instance", exist_ok=True)

    db.init_app(app)

    if bind:
        # Register endpoints only when serving (migrations import this factory too)
        MyWapp.bind(app, db)
        Swagger(app)  # Swagger UI at /apidocs by default
        # If you prefer /docs:
        # Swagger(app, config={"specs_route": "/docs/"})

    return app
```

### 1.3 `migrate_app.py` (Python driver for Alembic: diff → revision → upgrade)

```python
# migrate_app.py
import os, sys
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app_factory import create_app
from app_env import db, DATABASE_URL

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)  # ensure cwd

MIGRATIONS_DIR = BASE_DIR / "migrations"

def alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg

def ensure_dirs():
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    (MIGRATIONS_DIR / "versions").mkdir(parents=True, exist_ok=True)

def has_diff() -> bool:
    app = create_app(bind=False)
    with app.app_context():
        with db.engine.connect() as conn:
            mc = MigrationContext.configure(conn)
            diffs = compare_metadata(mc, db.metadata)
            return bool(diffs)

def autogen_if_needed(cfg: Config, message="autogenerate"):
    def _process(ctx, rev, directives):
        if not directives:
            return
        script = directives[0]
        if not getattr(script, "upgrade_ops", None) or script.upgrade_ops.is_empty():
            directives[:] = []
            print("No schema changes detected.")
    command.revision(cfg, message=message, autogenerate=True,
                     process_revision_directives=_process)

def main(argv=None):
    argv = argv or sys.argv[1:]
    cfg = alembic_config()
    ensure_dirs()

    if not argv:
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
        autogen_if_needed(cfg); return
    if cmd == "upgrade":
        command.upgrade(cfg, argv[1] if len(argv) > 1 else "head"); return
    if cmd == "downgrade":
        command.downgrade(cfg, argv[1] if len(argv) > 1 else "-1"); return
    if cmd in {"current", "history", "stamp"}:
        getattr(command, cmd)(cfg, *(argv[1:])); return
    print(f"Unknown command: {cmd}"); sys.exit(2)

if __name__ == "__main__":
    main()
```

### 1.4 `migrations/env.py` (Alembic env pointing at app metadata)

```python
# migrations/env.py
from logging.config import fileConfig
from alembic import context
from app_factory import create_app
from app_env import db, DATABASE_URL

config = context.config
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = db.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    app = create_app(bind=False)
    with app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 1.5 `app.py` (dev runner)

```python
# app.py
import sys, subprocess
from app_env import ENV
from app_factory import create_app

if __name__ == '__main__':
    if ENV == 'development':
        subprocess.run([sys.executable, "-m", "migrate_app"], check=True)

    app = create_app(bind=True)
    app.run(debug=True)
```

### 1.6 `.env` (example)

```
ENV=development
ENV_APP_TYPE=manager
DATABASE_URL=sqlite:///instance/app.db
```

**Run it:**

```bash
python app.py
# Swagger UI: http://127.0.0.1:5000/apidocs
```

---

## 2) Basic Example — Single Wapp, `User` model, CRUD

Create `users_wapp.py`:

```python
# users_wapp.py
from app_env import db
from wapp.core import Wapp

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    class WappModel:
        slug = "user"
        name = "User"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class UsersWapp(Wapp):
    class Models:
        user = User

    class Endpoints:
        _user = True   # autogenerate GET/GET(list)/POST/PUT/DELETE
```

Register it in `app_factory.py`:

```python
# app_factory.py (replace the MyWapp definition)
from users_wapp import UsersWapp

class MyWapp(Wapp):
    class Wapps:
        users = UsersWapp  # available under /users
```

Restart. You’ll have:

* `GET /users/user/` — list users
* `POST /users/user/` — create
* `GET /users/user/<id>` — get
* `PUT /users/user/<id>` — update
* `DELETE /users/user/<id>` — delete

---

## 3) Add a nested stats wapp under Users

Create `users_stats_wapp.py` with custom endpoints:

```python
# users_stats_wapp.py
from flask import jsonify
from wapp.core import Wapp
from wapp.endpoint_base import WappEndpoint
from app_env import db
from users_wapp import User

class UsersCountEndpoint(WappEndpoint):
    """User count
    ---
    tags: [Users Stats]
    responses:
      200:
        description: Count of users
        schema:
          type: object
          properties: { count: { type: integer } }
    """
    class Meta:
        method = 'GET'
        pattern = '/stats/count'
        name = 'Users Count'
        description = 'Total number of users'

    def handle(self, request, query, path, body):
        total = db.session.query(User).count()
        return jsonify({"count": total})

class UsersTopDomainsEndpoint(WappEndpoint):
    """Users top email domains
    ---
    tags: [Users Stats]
    responses:
      200:
        description: List of domains
        schema:
          type: array
          items: { type: string }
    """
    class Meta:
        method = 'GET'
        pattern = '/stats/top-domains'
        name = 'Users Top Domains'
        description = 'Top email domains'
    def handle(self, request, query, path, body):
        rows = db.session.execute("""
            SELECT substr(email, instr(email, '@')+1) AS domain, COUNT(*) c
            FROM user GROUP BY domain ORDER BY c DESC LIMIT 5
        """)
        return jsonify([r[0] for r in rows])

class UsersRecentEndpoint(WappEndpoint):
    """Recent users
    ---
    tags: [Users Stats]
    responses:
      200:
        description: Recent users
        schema:
          type: array
          items: { type: object }
    """
    class Meta:
        method = 'GET'
        pattern = '/stats/recent'
        name = 'Users Recent'
        description = 'Most recent users'
    def handle(self, request, query, path, body):
        rows = User.query.order_by(User.id.desc()).limit(5).all()
        return self.to_response(rows)

class UsersStatsWapp(Wapp):
    class Endpoints:
        users_count = UsersCountEndpoint
        users_top_domains = UsersTopDomainsEndpoint
        users_recent = UsersRecentEndpoint
```

Nest it inside `UsersWapp`:

```python
# users_wapp.py
from users_stats_wapp import UsersStatsWapp

class UsersWapp(Wapp):
    class Models:
        user = User
    class Endpoints:
        _user = True
    class Wapps:
        stats = UsersStatsWapp   # routes under /users/stats/...
```

Now you have:

* `/users/stats/count`
* `/users/stats/top-domains`
* `/users/stats/recent`

---

## 4) Add a side-by-side Meetings wapp

`meetings_wapp.py`:

```python
# meetings_wapp.py
from app_env import db
from wapp.core import Wapp

class Meeting(db.Model):
    __tablename__ = 'meeting'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text)

    class WappModel:
        slug = "meeting"
        name = "Meeting"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MeetingsWapp(Wapp):
    class Models:
        meeting = Meeting
    class Endpoints:
        _meeting = True   # full CRUD (we’ll refine in step 5)
```

Register in the root:

```python
# app_factory.py
from users_wapp import UsersWapp
from meetings_wapp import MeetingsWapp

class MyWapp(Wapp):
    class Wapps:
        users = UsersWapp
        meetings = MeetingsWapp
```

---

## 5) Conditional Meetings endpoints by `ENV_APP_TYPE`

* `ENV_APP_TYPE=manager` → full CRUD + a stats endpoint
* `ENV_APP_TYPE=public` → only `list` + `get`

Update `meetings_wapp.py`:

```python
# meetings_wapp.py
import os
from flask import jsonify
from app_env import db, ENV_APP_TYPE
from wapp.core import Wapp
from wapp.endpoint_base import WappEndpoint

class Meeting(db.Model):
    __tablename__ = 'meeting'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text)

    class WappModel:
        slug = "meeting"
        name = "Meeting"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# Optional manager-only stats
class MeetingsCountEndpoint(WappEndpoint):
    """Meetings count
    ---
    tags: [Meetings]
    responses:
      200:
        description: Count of meetings
        schema:
          type: object
          properties: { count: { type: integer } }
    """
    class Meta:
        method = 'GET'
        pattern = '/meeting/stats/count'
        name = 'Meetings Count'
    def handle(self, request, query, path, body):
        total = db.session.query(Meeting).count()
        return jsonify({"count": total})

class MeetingsWapp(Wapp):
    class Models:
        meeting = Meeting

    # Decide endpoints based on ENV_APP_TYPE
    if ENV_APP_TYPE == "public":
        # only list + get
        class Endpoints:
            _meeting = {
                "list": True,
                "get": True,
                # explicitly disable others
                "create": False,
                "update": False,
                "delete": False,
            }
    else:  # manager (default)
        class Endpoints:
            _meeting = True
            meetings_count = MeetingsCountEndpoint
```

Set in `.env`:

```
ENV_APP_TYPE=public   # or manager
```

Restart and observe Meetings routes adapt accordingly.

---

Yes—overriding a default (auto-generated) CRUD endpoint is built in. You’ve got three useful patterns:

## 1) Override **one action** via the `_model` dict

Give a custom class for the action you want, let Wapp autogenerate the rest.

```python
from wapp.core import Wapp
from wapp.generic_endpoints import Get  # base for GET /<id>
from app_env import db
from users_wapp import User

class UserGetCustom(Get):
    """Get user with extra joins/guards
    ---
    tags: [User]
    responses:
      200:
        description: OK
    """
    # keep same route as the auto one:
    class Meta(Get.Meta):
        method = 'GET'
        pattern = f"/{User.WappModel.slug}/<int:id>"
        name = "User Get (custom)"

    def handle(self, request, query, path, body):
        # your custom behavior
        obj = self.model.query.get(path['id'])
        if not obj:
            return self.to_response({"error": "Not found"}), 404
        # e.g., add computed fields
        data = obj.as_dict()
        data["role"] = "admin" if obj.username == "root" else "user"
        return self.to_response(data)

class UsersWapp(Wapp):
    class Models:
        user = User
    class Endpoints:
        _user = {
            "get": UserGetCustom,  # 👈 override GET /user/<id>
            # list/create/update/delete will be auto-generated
        }
```

## 2) Override **multiple actions**, disable others

You can mix custom classes, `True` (autogen), and `False` (disable).

```python
class UsersWapp(Wapp):
    class Models:
        user = User
    class Endpoints:
        _user = {
            "get": UserGetCustom,  # custom
            "list": True,          # autogen
            "create": False,       # disabled
            "update": True,        # autogen
            # "delete": False,     # disabled by default if not present
        }
```

## 3) Replace **all** CRUD endpoints with custom ones

Provide a class for each action; nothing will be auto-generated.

```python
class UserListCustom(List):  # inherit the matching base for convenience
    class Meta(List.Meta):
        method = 'GET'
        pattern = f"/{User.WappModel.slug}/"
        name = "User List (custom)"
    def handle(self, request, query, path, body):
        return self.to_response(User.query.order_by(User.id.desc()).all())

class UsersWapp(Wapp):
    class Models:
        user = User
    class Endpoints:
        _user = {
            "get":   UserGetCustom,
            "list":  UserListCustom,
            "create": UserCreateCustom,
            "update": UserUpdateCustom,
            "delete": UserDeleteCustom,
        }
```

### Important notes

* **Set `Meta.method` and `Meta.pattern` on custom classes.**
  The auto-generator fills these for you, but when you override with a custom class, *you* must declare them. Use:

  ```python
  method  = Wapp.CRUD_ACTIONS['get']['method']      # 'GET'
  
  from wherever import what_tickles_your_fancy as custom_pattern
  pattern = custom_pattern or Wapp.CRUD_ACTIONS['get']['pattern'].format(model_slug=User.WappModel.slug)
  ```

  or just hardcode as shown.

* **Inherit the right base** (`Get`, `List`, `Create`, `Update`, `Delete`) so you keep the same call shape and helpers (`to_response`, `request_model` parsing, etc.).

* **Swagger docstring**: add a YAML docstring (`"""Summary\n---\n..."""`) to your custom class; Wapp wraps endpoint classes into plain functions so Flasgger can read that docstring.

* **Disable collisions**: don’t also set `_user = True` if you’re overriding via dict; you’ll end up with two handlers on the same path.

* **Custom request/response schemas**: you can add `request_model`/`response_model` to your `Meta` (if your base uses them) or document via YAML.

That’s it—drop a custom class into the `_model` dict for the action you want to override, and you’re in full control while keeping the rest auto-generated.

---

## Migrations (autogenerate + apply)

Every time you add/edit models:

```bash
# From project root
python -m migrate_app          # creates a revision when needed and upgrades to head
# or
python -m migrate_app check    # exit code 1 if there are diffs
python -m migrate_app revision # force creating a new revision (if diffs)
python -m migrate_app upgrade  # apply
```

Alembic reads your models via `db.metadata` inside `migrations/env.py` and your `app_factory.create_app(bind=False)` (which avoids registering routes during migration).

---

## Swagger UI

* Default: **`/apidocs/`**
* Change to `/docs/` by passing `Swagger(app, config={"specs_route": "/docs/"})` in `create_app`.

If you author custom endpoints, you can put minimal YAML in their docstrings (as shown in stats endpoints) to enrich the UI.

---

## Routing Primer

* Root wapp: `MyWapp`
* Child wapps mounted by attribute name:

  * `users` → `/users/...`
  * `meetings` → `/meetings/...`
* CRUD paths are built from each model’s `WappModel.slug`.

  * `User.WappModel.slug = "user"` ⇒ `/users/user/...`
  * `Meeting.WappModel.slug = "meeting"` ⇒ `/meetings/meeting/...`
* Custom endpoints set `Meta.pattern`, e.g. `'/stats/count'` under the current wapp prefix, or fully explicit like `'/meeting/stats/count'`.

> If you want `/users/` (no double `user/user`), set `slug=''` and adjust patterns—or keep the explicit style as shown for clarity.

---

## Troubleshooting

* **Internal Server Error at `/apispec_1.json`**: usually malformed Swagger YAML or a view object Flasgger can’t inspect. Wapp wraps endpoint classes into function views so Flasgger can parse their docstrings; if you wrote custom views, ensure they’re functions or carry docstrings properly.
* **SQLite “unable to open database file”**: ensure absolute URL normalization (provided in `app_env.py`) and that `instance/` exists.
* **Duplicate endpoints assertion**: don’t call `bind()` during migrations; this guide uses `create_app(bind=False)` in Alembic.

---

## Summary

You now have:

* A **root wapp** with multiple child wapps
* **Auto-CRUD** for models with a simple `WappModel` meta and `_model = True`
* **Nested wapps** for organizational endpoints like stats
* A **conditional API surface** driven by environment (`ENV_APP_TYPE`)
* One-command **migrations** and **Swagger UI** out of the box

Happy shipping. 🛠️🚀
