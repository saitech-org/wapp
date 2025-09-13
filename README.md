# Wapp Framework - Quickstart Guide

Wapp is a modular, plug-and-play framework for building Flask APIs with automatic CRUD endpoints, model registration, and Alembic migrations. This guide will help you get started as a developer using Wapp as an external package.

---

## 🚀 Getting Started

### 1. Install Wapp and Dependencies

Install Wapp from PyPI (or your package registry) and its dependencies:

```bash
pip install saitech-wapp flask flask_sqlalchemy alembic python-dotenv pydantic
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
from wapp import Wapp


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
from wapp import Wapp


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

**IMPORTANT:**
To ensure Alembic autogenerate detects your models, you must import your SQLAlchemy db instance in `migrations/env.py` and set:

```python
from env import db  # Use the same db instance as your app
# ...
target_metadata = db.metadata
```

This ensures Alembic uses the same metadata as your app and can autogenerate migrations for your models.

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
