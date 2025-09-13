# Wapp Framework — Quickstart Guide

Wapp is a modular framework for building Flask APIs with automatic CRUD endpoints, nested applications, and Alembic migrations. This guide will help you quickly set up your project and effectively define your models, endpoints, and customize request and response types.

## Quick Setup Guide

### TLDR

```aiignore
mkdir my_project
cd my_project
pip install saitech-wapp
wapp-init
```

### Prerequisites

Make sure you have Python (3.6 or higher) installed. Then install the required packages via the command line:

```bash
pip install saitech-wapp flask flask_sqlalchemy alembic flasgger python-dotenv pydantic
```

### Bootstrap Your Project

Use the CLI to initialize a new Wapp project:

```bash
python -m cli
```

This command will create a new directory with necessary files like `app.py`, `app_env.py`, and others to get you started right away.

### Running the Application

After bootstrapping, run your application using:

```bash
python app.py
```

Your API will be available at `http://127.0.0.1:5000/apidocs`.

---

## Composing Blocks: How It Works

### 1. Flask

Flask is a lightweight WSGI web application framework for Python. It provides the basic structure for web applications, handling routing, request/response management, and middleware integration.

### 2. SQLAlchemy

SQLAlchemy is an ORM (Object-Relational Mapping) tool that abstracts database interactions, allowing you to work with database records as Python objects. You define models that represent your database tables, and SQLAlchemy handles querying and data manipulation.

### 3. Wapp Framework

Wapp builds on Flask and SQLAlchemy, providing additional features like:
- Automatic generation of CRUD endpoints based on your models.
- Nested applications, allowing you to group related functionality.
- Integration with Alembic for database migrations.

---

## Defining Models

Defining a model in Wapp involves creating a class that extends `db.Model` from SQLAlchemy.

### Basic Structure

```python
from app_env import db

class YourModel(db.Model):
    __tablename__ = 'your_model'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    class WappModel:
        slug = "your_model"  # URL slug for the model
        name = "Your Model"   # Display name in documentation

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

Endpoints in Wapp are classes that handle API requests for your models. You can use auto-generated endpoints or create custom ones.

### Creating Endpoints

You can create an endpoint by extending `WappEndpoint`. Here's the basic structure:

```python
from wapp.core import Wapp
from wapp.endpoint_base import WappEndpoint
from pydantic import BaseModel as PydanticModel

class YourRequestModel(PydanticModel):
    name: str  # Request body schema

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
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
    """
    class Meta:
        method = 'GET'
        pattern = '/your_model/<int:id>'
        name = 'Get YourModel'
        request_model = YourRequestModel
        response_model = YourResponseModel

    def handle(self, request, query, path, body):
        # Logic for handling the request
        obj = YourModel.query.get(path['id'])
        if not obj:
            return {"error": "Not Found"}, 404
        return obj.as_dict()
```

### Using Auto-CRUD Generation

If your endpoint class includes the `_model` attribute set to `True`, Wapp will automatically generate CRUD functionality for you.

### Example: UsersWapp with Auto-CRUD and Custom Endpoints

```python
class UsersWapp(Wapp):
    class Models:
        user = User  # Model to expose

    class Endpoints:
        _user = True  # Automatically generate CRUD endpoints

        # Custom endpoint example
        class UsersStatsEndpoint(WappEndpoint):
            """ Retrieve user statistics
            ---
            tags: [User Stats]
            responses:
              200:
                description: User statistics
                schema:
                  type: object
                  properties:
                    total_users:
                      type: integer
            """
            class Meta:
                method = 'GET'
                pattern = '/stats'
                name = 'User Stats'

            def handle(self, request, query, path, body):
                total_users = User.query.count()
                return {"total_users": total_users}
        
        stats = UsersStatsEndpoint  # Register custom endpoint

```

---

## Request and Response Types

- **Request Models:** You can define request bodies using Pydantic models, which allows you to perform validation easily.

- **Response Models:** Similarly, you can define the structure of responses using Pydantic models for clear API documentation and consistent data.

### Example Request and Response Models

```python
class CreateUserRequest(PydanticModel):
    username: str
    email: str

class CreateUserResponse(PydanticModel):
    id: int
    username: str
    email: str
```

### Customizing Endpoints with Request/Response Models

When defining endpoints, you can specify these models in the `Meta` class to clarify how the API interacts with users.

```python
class CreateUserEndpoint(WappEndpoint):
    """ Create a new user
    ---
    tags: [User]
    requestBody:
      required: true
      content:
        application/json:
          schema: CreateUserRequest
    responses:
      201:
        description: User created
        schema: CreateUserResponse
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

With Wapp, you can rapidly develop robust Flask APIs using SQLAlchemy for database management. By following this guide, you’ll be able to set up a new project, define your models, create endpoints tailored to your application's needs, and utilize request/response types for effective data handling.

For more advanced topics, such as migrations and nested applications, please refer to the complete documentation or explore the examples provided in the project.

Happy coding! 🚀
