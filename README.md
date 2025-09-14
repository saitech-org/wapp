# Wapp — Quickstart Guide

Wapp is a modular framework for building Flask APIs with automatic CRUD endpoints, nested applications, and Alembic migrations. This guide will help you quickly set up your project, define your models and endpoints, and customize request and response types.

---

## Quick Setup Guide

### TL;DR

```bash
mkdir my_project && cd my_project
pip install saitech-wapp
wapp-init
python app.py
```

Your API docs will be available at:
[http://127.0.0.1:5000/apidocs/](http://127.0.0.1:5000/apidocs/)

---

### Prerequisites

* **Python 3.8+** (Wapp and its dependencies require at least Python 3.8).
* Install the package using your preferred tool:

```bash
pip install saitech-wapp
```

Or with Poetry/PDM/UV:

```bash
poetry add saitech-wapp
# or
pdm add saitech-wapp
# or
uv add saitech-wapp
```

---

### Bootstrap Your Project

Use the CLI to initialize a new Wapp project:

```bash
wapp-init
```

This command will create necessary files like `app.py`, `app_env.py`, `migrate_app.py`, and `create_app.py`.

*(If you installed in editable mode, you can also run `python -m cli`.)*

---

### Running the Application

Start your application:

```bash
python app.py
```

Open the API docs at:
[http://127.0.0.1:5000/apidocs/](http://127.0.0.1:5000/apidocs/)

---

### Database Migrations

Initialize the database with Alembic:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## Composing Blocks: How It Works

### 1. Flask

Flask provides the basic structure for routing, request/response management, and middleware.

### 2. SQLAlchemy

SQLAlchemy abstracts database interactions via ORM models.

### 3. Wapp

Wapp builds on Flask and SQLAlchemy, adding:

* Automatic CRUD endpoint generation
* Nested applications for grouping related functionality
* Integration with Alembic migrations

---

## Defining Models

Define models by extending `db.Model` from SQLAlchemy:

```python
from app_env import db

class YourModel(db.Model):
    __tablename__ = 'your_model'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    class WappModel:
        slug = "your_model"
        name = "Your Model"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### Example: User Model

```python
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
```

---

## Defining Endpoints

Endpoints are classes that handle API requests for your models. You can let Wapp auto-generate CRUD endpoints or define custom ones.

### Creating a Custom Endpoint

```python
from wapp.core import Wapp
from wapp.endpoint_base import WappEndpoint
from pydantic import BaseModel as PydanticModel

class YourRequestModel(PydanticModel):
    name: str

class YourResponseModel(PydanticModel):
    id: int
    name: str

class YourEndpoint(WappEndpoint):
    """ Get your model by ID
    ---
    tags: [Your Model]
    responses:
      200:
        description: Successful retrieval
    """
    class Meta:
        method = 'GET'
        pattern = '/your_model/<int:id>'
        name = 'Get YourModel'
        request_model = YourRequestModel
        response_model = YourResponseModel

    def handle(self, request, query, path, body):
        obj = YourModel.query.get(path['id'])
        if not obj:
            return {"error": "Not Found"}, 404
        return obj.as_dict()
```

### Using Auto-CRUD Generation

If your endpoint class includes `_model = True`, Wapp generates CRUD endpoints automatically.

### Example: UsersWapp with Auto-CRUD + Custom Endpoint

```python
class UsersWapp(Wapp):
    class Models:
        user = User

    class Endpoints:
        _user = True  # Auto-CRUD for User

        class UsersStatsEndpoint(WappEndpoint):
            """ Retrieve user statistics
            ---
            tags: [User Stats]
            responses:
              200:
                description: User statistics
            """
            class Meta:
                method = 'GET'
                pattern = '/stats'
                name = 'User Stats'

            def handle(self, request, query, path, body):
                total_users = User.query.count()
                return {"total_users": total_users}

        stats = UsersStatsEndpoint
```

---

## Request and Response Types

Define request/response bodies with **Pydantic models** for validation and documentation.

```python
class CreateUserRequest(PydanticModel):
    username: str
    email: str

class CreateUserResponse(PydanticModel):
    id: int
    username: str
    email: str
```

Attach them in your endpoint `Meta`:

```python
class CreateUserEndpoint(WappEndpoint):
    """ Create a new user
    ---
    tags: [User]
    """
    class Meta:
        method = 'POST'
        pattern = '/user'
        name = 'Create User'
        request_model = CreateUserRequest
        response_model = CreateUserResponse

    def handle(self, request, query, path, body):
        new_user = User(username=body.username, email=body.email)
        db.session.add(new_user)
        db.session.commit()
        return new_user.as_dict(), 201
```

---

## Conclusion

With Wapp, you can rapidly build robust Flask APIs with SQLAlchemy models, Alembic migrations, and auto-generated CRUD.

* Initialize with `wapp-init`
* Define models via SQLAlchemy
* Expose them with auto-CRUD or custom endpoints
* Use Pydantic for validation and response typing

For advanced usage (nested apps, migrations, customization), see the full documentation and included examples.

Happy coding 🚀

```
```
