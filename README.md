# Wapp Framework - Quickstart Guide

Wapp is a modular, plug-and-play framework for building Flask APIs with automatic CRUD endpoints, model registration, and Alembic migrations. This guide will help you get started as a developer.

---

## 🚀 Getting Started: Step-by-Step

### 1. Install Wapp and Dependencies

```bash
pip install wapp flask flask_sqlalchemy alembic python-dotenv pydantic
```

### 2. Initialize Your Project

Create a new directory and initialize a basic Flask project structure:

```
myproject/
  app.py
  env.py
  mywapp/
    __init__.py
    wapp.py
  migrations/
  alembic.ini
```

- `env.py` will hold your DB and environment config.
- `mywapp/wapp.py` will define your first wapp.

### 3. Configure the Environment

In `env.py`:
```python
import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')
db = SQLAlchemy()
```

Create a `.env` file (optional):
```
DATABASE_URL=sqlite:///app.db
AUTO_MIGRATE=true
ENV=development
```

### 4. Define Your First Wapp

In `mywapp/wapp.py`:
```python
from env import db
from wapp.core import Wapp

class Foo(db.Model):
    __tablename__ = 'foo'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class WappModel:
        slug = "foo"
        name = "Foo"
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MyWapp(Wapp):
    class Models:
        foo = Foo
    class Endpoints:
        _foo = True  # Enable auto-CRUD for Foo
```

### 5. Create the Main App

In `app.py`:
```python
from flask import Flask
from env import db, DATABASE_URL
from mywapp.wapp import MyWapp
from wapp.core import Wapp

class MainWapp(Wapp):
    class Wapps:
        mywapp = MyWapp

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    db.init_app(app)
    MainWapp.register_wapp(app, db)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
```

### 6. Set Up Alembic for Migrations

- Initialize Alembic (if not already):
  ```bash
  alembic init migrations
  ```
- Edit `alembic.ini` to set `script_location = migrations` and `sqlalchemy.url = sqlite:///app.db` (or your DB URI).
- Edit `migrations/env.py` to import your models and set `target_metadata = db.metadata`.

### 7. Run Migrations

- To auto-generate and apply migrations:
  ```bash
  python -m wapp.migrate
  # or, if installed as a CLI:
  wapp-migrate
  ```

### 8. Run the App

```bash
export FLASK_APP=app.py
flask run
```

### 9. Test Your API

- List Foos: `GET /mywapp/foo/`
- Create Foo: `POST /mywapp/foo/` (with JSON body)
- Get Foo: `GET /mywapp/foo/<id>`
- Update Foo: `PUT /mywapp/foo/<id>`
- Delete Foo: `DELETE /mywapp/foo/<id>`

---

## 1. Project Structure

```
project/
  flaskapp.py         # Main Flask app
  env.py              # Environment and DB config
  demo/wapp.py        # Example wapp (DemoWapp)
  nested/things/wapp.py # Nested wapp (ThingsWapp)
  wapp/core.py        # Wapp base class
  wapp/endpoint_base.py # Endpoint base class
  wapp/migrate.py     # Migration script
  migrations/         # Alembic migrations
  alembic.ini         # Alembic config
```

---

## 2. Defining a Wapp

A wapp is a class inheriting from `Wapp`. It can define:
- **Models**: SQLAlchemy models with a `WappModel` inner class (for metadata).
- **Endpoints**: Custom endpoints (subclass `WappEndpoint`) or auto-CRUD for models.

Example:
```python
from env import db
from wapp.core import Wapp
from wapp.endpoint_base import WappEndpoint

class Foo(db.Model):
    __tablename__ = 'foo'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class WappModel:
        slug = "foo"
        name = "Foo"
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class DemoWapp(Wapp):
    class Models:
        foo = Foo
    class Endpoints:
        _foo = True  # Enable auto-CRUD for Foo
```

---

## 3. Registering Wapps

In your main app (e.g. `flaskapp.py`):

```python
from flask import Flask
from env import db, DATABASE_URL
from demo.wapp import DemoWapp
from wapp.core import Wapp

class MainWapp(Wapp):
    class Wapps:
        demo = DemoWapp

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    db.init_app(app)
    MainWapp.register_wapp(app, db)
    return app
```

---

## 4. Automatic Migrations

- **Development**: Migrations run automatically if `AUTO_MIGRATE=true` in `.env`.
- **Manual**: Run `python -m wapp.migrate` or `wapp-migrate` to generate/apply migrations.

---

## 5. Adding Endpoints

- **Custom**: Subclass `WappEndpoint` and implement `handle()`.
- **Auto-CRUD**: In `Endpoints`, set `_modelname = True` or a list of actions (e.g. `["list", "get"]`).

---

## 6. Environment Variables

- `DATABASE_URL`: SQLAlchemy DB URI (default: `sqlite:///app.db`)
- `AUTO_MIGRATE`: Run migrations on startup (default: `true`)
- `ENV`: Set to `development` for auto-migrate

---

## 7. Running the App

```bash
pip install -r requirements.txt
export FLASK_APP=flaskapp.py
flask run
```

Or, for manual migration:
```bash
python -m wapp.migrate
python flaskapp.py
```

---

## 8. Creating a New Wapp

1. Create a new folder (e.g. `mywapp/`).
2. Add your models and endpoints.
3. Register in `MainWapp.Wapps`.

---

## 9. API Usage

- All endpoints are registered as `/wappname/model/` or `/wappname/endpoint/`.
- Use standard REST verbs (GET, POST, PUT, DELETE).

---

## 10. Troubleshooting

- If migrations fail, check your model changes and DB URI.
- For custom logic, subclass and override as needed.

---

## 11. More

- See `demo/wapp.py` and `nested/things/wapp.py` for examples.
- See `wapp/core.py` for advanced customization.

---

Happy hacking!
