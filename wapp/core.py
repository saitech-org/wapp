from typing import List, Tuple, Type

from flask import Blueprint
from sqlalchemy.orm import DeclarativeMeta
from inspect import isclass
from .endpoint_base import WappEndpoint

# --- Add near other imports at the top of the file ---
from sqlalchemy import Integer, String, Boolean, Float, DateTime, Text, LargeBinary
from sqlalchemy.sql.schema import Column

SQLA_Model = DeclarativeMeta


def is_sqla_model(obj):
    try:
        return isclass(obj) and issubclass(obj, SQLA_Model)
    except Exception:
        return False


class Wapp:
    name: str = ""
    db = None  # Bind the SQLAlchemy db instance here

    @classmethod
    def bind(cls, app, db_instance, url_prefix=None):
        """
        Binds the db to all wapps/endpoints, builds blueprint, and registers it with the Flask app.
        Only the main Wapp should be registered; nested Wapps are included via blueprint nesting.
        Ensures endpoints are generated for all wapps before binding db, so db is available on all endpoints.
        """
        cls._cached_endpoints = None
        cls._blueprint = None
        cls._generate_endpoints_recursive()
        cls._bind_db_recursive(db_instance)
        cls._blueprint = cls._build_blueprint(url_prefix=url_prefix)
        app.register_blueprint(cls._blueprint)

    CRUD_ACTIONS = {
        'get': {'method': 'GET', 'pattern': '/{model_slug}/<int:id>'},
        'list': {'method': 'GET', 'pattern': '/{model_slug}/'},
        'create': {'method': 'POST', 'pattern': '/{model_slug}/'},
        'update': {'method': 'PUT', 'pattern': '/{model_slug}/<int:id>'},
        'delete': {'method': 'DELETE', 'pattern': '/{model_slug}/<int:id>'}
    }

    _cached_endpoints = None  # Class-level cache for endpoints
    _blueprint = None  # Class-level cache for blueprint

    @classmethod
    def bind_db(cls, db_instance):
        if getattr(cls, 'db', None) is db_instance:
            return  # Already bound
        cls.db = db_instance
        # Always refresh endpoints when binding db
        for _, endpoint_cls in cls.get_endpoints(fresh=True):
            setattr(endpoint_cls, 'db', db_instance)
        # Bind db to nested wapps
        wapps = cls.get_wapps()
        if not wapps:
            return
        for _, wapp in wapps:
            wapp.bind_db(db_instance)

    @classmethod
    def _generate_endpoints_recursive(cls):
        """
        Ensure all endpoints (including nested Wapps) are generated before db binding.
        """
        cls.get_endpoints(fresh=True)
        for _, wapp in cls.get_wapps():
            wapp._generate_endpoints_recursive()

    @classmethod
    def _bind_db_recursive(cls, db_instance):
        """
        Bind db to this Wapp, all endpoints (after CRUD generation), and all nested Wapps.
        """
        cls.db = db_instance
        for _, endpoint_cls in cls.get_endpoints():
            setattr(endpoint_cls, 'db', db_instance)
        for _, wapp in cls.get_wapps():
            wapp._bind_db_recursive(db_instance)

    @classmethod
    def _build_blueprint(cls, url_prefix=None, parent_prefix=""):
        """
        Build a blueprint including this Wapp's endpoints and all nested Wapps, using attribute name as slug.
        """
        this_prefix = url_prefix or ""
        full_prefix = (parent_prefix.rstrip("/") + this_prefix).replace("//", "/")
        bp = Blueprint(cls.__name__, __name__, url_prefix=this_prefix)
        # Register this Wapp's endpoints
        for name, endpoint_cls in cls.get_endpoints():
            meta = getattr(endpoint_cls, 'Meta', None)
            if meta and meta.pattern and meta.method:
                view_func = cls._wrap_endpoint_for_flasgger(endpoint_cls)
                endpoint_name = f"{bp.name}_{endpoint_cls.__module__}__{endpoint_cls.__qualname__}".replace(".", "_")
                api_path = (full_prefix.rstrip("/") + meta.pattern).replace("//", "/")
                print(f"Registering endpoint: {meta.method} {api_path} -> {endpoint_cls.__name__} ({meta.name}) as {endpoint_name}")
                bp.add_url_rule(
                    meta.pattern,
                    endpoint=endpoint_name,
                    view_func=view_func,
                    methods=[meta.method]
                )
        # Register nested wapps using attribute name as slug
        for wapp_name, wapp_cls in cls.get_wapps():
            nested_prefix = f"/{wapp_name}"
            nested_bp = wapp_cls._build_blueprint(url_prefix=nested_prefix, parent_prefix=full_prefix)
            bp.register_blueprint(nested_bp)
        return bp

    @classmethod
    def blueprint(cls):
        """
        Returns the cached blueprint after binding, or raises if not bound.
        """
        if cls._blueprint is None:
            raise RuntimeError("Wapp must be bound before accessing blueprint.")
        return cls._blueprint

    @classmethod
    def get_models(cls):
        models = getattr(cls, 'Models', None)
        if not models:
            return []
        return [
            (name, model)
            for name, model in models.__dict__.items()
            if isclass(model) and hasattr(model, 'WappModel')
        ]

    @classmethod
    def get_endpoints(cls, fresh=False):
        if not fresh and cls._cached_endpoints is not None:
            return cls._cached_endpoints

        endpoints = getattr(cls, 'Endpoints', None)
        if not endpoints or not hasattr(endpoints, '__dict__'):
            cls._cached_endpoints = []
            return []
        result = []
        to_set = {}  # Collect new endpoint attributes to set after iteration
        endpoints_dict = dict(endpoints.__dict__.items())  # Copy for safe iteration
        # 1. Explicit endpoint classes
        for name, view in endpoints_dict.items():
            if isclass(view) and issubclass(view, WappEndpoint):
                result.append((name, view))
        # 2. CRUD auto-generation for _model attributes
        models = dict(cls.get_models())
        for name, value in endpoints_dict.items():
            if name.startswith('_'):
                model_name = name[1:]
                if model_name not in models:
                    continue
                model = models[model_name]
                meta = getattr(model, 'WappModel', None)
                if not meta or not hasattr(meta, 'slug'):
                    raise ValueError(f"Model '{model_name}' missing WappModel.slug.")
                # Enhanced logic for _model field
                if isinstance(value, dict):
                    for action in cls.CRUD_ACTIONS:
                        v = value.get(action, None)
                        if v is False or None:
                            continue  # Explicitly disabled
                        if v and isclass(v) and issubclass(v, WappEndpoint):
                            result.append((f"{model_name}_{action}", v))
                            to_set[f"{model_name}_{action}"] = v
                        elif v:
                            endpoint_cls = cls._generate_crud_endpoint(model, meta, action)
                            result.append((f"{model_name}_{action}", endpoint_cls))
                            to_set[f"{model_name}_{action}"] = endpoint_cls
                        # If v is not None, not a class, and not False, skip (invalid)
                elif value:
                    # If value is truthy (e.g. True), generate all endpoints
                    for action in cls.CRUD_ACTIONS:
                        endpoint_cls = cls._generate_crud_endpoint(model, meta, action)
                        result.append((f"{model_name}_{action}", endpoint_cls))
                        to_set[f"{model_name}_{action}"] = endpoint_cls
        # Set new endpoint attributes after iteration
        for k, v in to_set.items():
            setattr(endpoints, k, v)
        cls._cached_endpoints = result
        return result

    @classmethod
    def _generate_crud_endpoint(cls, model, meta, action):
        from .generic_endpoints import Get, List, Create, Update, Delete
        db = cls.db
        slug = meta.slug
        name = meta.name
        # Map action to generic endpoint class
        endpoint_map = {
            'get': Get,
            'list': List,
            'create': Create,
            'update': Update,
            'delete': Delete,
        }
        base_cls = endpoint_map[action]
        # Set up Meta attributes dynamically
        pattern = cls.CRUD_ACTIONS[action]['pattern'].format(model_slug=slug)
        method = cls.CRUD_ACTIONS[action]['method']
        description = f"Auto-generated {action} endpoint for {name}"

        swagger_doc = cls._build_swagger_doc(model, meta, action, slug, pattern)
        # Dynamically create a subclass and bind model/meta/db
        class_attrs = {
            "__doc__": swagger_doc,
            'model': model,
            'meta': meta,
            'db': db,
            'Meta': type('Meta', (base_cls.Meta,), {
                'pattern': pattern,
                'method': method,
                'name': f"{name} {action.capitalize()}",
                'description': description,
                'request_model': getattr(base_cls.Meta, 'request_model', None),
                'response_model': getattr(base_cls.Meta, 'response_model', None),
            })
        }
        endpoint_cls = type(f"{model.__name__}_{action.capitalize()}Endpoint", (base_cls,), class_attrs)
        return endpoint_cls

    @classmethod
    def get_wapps(cls) -> List[Tuple[str, Type["Wapp"]]]:
        wapps = getattr(cls, 'Wapps', None)
        if not wapps:
            return []

        return [
            (name, wapp)
            for name, wapp in wapps.__dict__.items()
            if isclass(wapp) and issubclass(wapp, Wapp) and wapp is not cls
        ]

    # --- Inside class Wapp: add helpers ---

    @staticmethod
    def _sa_type_to_swagger_type(col_type):
        """Map common SQLAlchemy types to Swagger (OpenAPI 2.0) types/formats."""
        # Handle parametrized types (e.g., String(50))
        base = type(col_type)
        if base is Integer:
            return {"type": "integer", "format": "int32"}
        if base is Float:
            return {"type": "number", "format": "float"}
        if base is Boolean:
            return {"type": "boolean"}
        if base is DateTime:
            return {"type": "string", "format": "date-time"}
        if base is Text:
            return {"type": "string"}
        if base is LargeBinary:
            return {"type": "string", "format": "byte"}
        if base is String:
            return {"type": "string"}
        # default fallback
        return {"type": "string"}

    @classmethod
    def _model_swagger_schema(cls, model):
        """
        Build a minimal schema definition from a SQLAlchemy model.
        """
        props = {}
        required = []
        for col in model.__table__.columns:
            # Skip relationship-only attributes; here we only have Columns
            if not isinstance(col, Column):
                continue
            p = cls._sa_type_to_swagger_type(col.type)
            if col.doc:  # optional: use SQLAlchemy Column.doc as description
                p = dict(p)
                p["description"] = col.doc
            props[col.name] = p

            # required if not nullable and no server default (keep it simple)
            if not col.nullable and not col.primary_key and col.default is None and col.server_default is None:
                required.append(col.name)

        schema = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
        return schema

    @classmethod
    def _build_swagger_doc(cls, model, meta, action, slug, pattern):
        """
        Return a YAML docstring for Flasgger based on action and model.
        """
        tag = meta.name
        model_schema = cls._model_swagger_schema(model)

        # Response schema per action
        if action == "list":
            response_schema = {"type": "array", "items": model_schema}
            summary = f"List {meta.name}"
            params_yaml = ""  # could add query params later (page, size, filters)
        elif action == "get":
            response_schema = model_schema
            summary = f"Get {meta.name} by id"
            params_yaml = """
  - name: id
    in: path
    type: integer
    required: true
    description: Record ID
            """
        elif action == "create":
            response_schema = model_schema
            summary = f"Create {meta.name}"
            # body schema (exclude primary key from required, usually auto)
            body_schema = dict(model_schema)
            if "required" in body_schema:
                body_schema = dict(body_schema)
                body_schema["required"] = [r for r in body_schema["required"] if r != "id"]
            params_yaml = f"""
  - in: body
    name: body
    required: true
    schema: {body_schema!r}
            """
        elif action == "update":
            response_schema = model_schema
            summary = f"Update {meta.name}"
            body_schema = dict(model_schema)
            params_yaml = f"""
  - name: id
    in: path
    type: integer
    required: true
    description: Record ID
  - in: body
    name: body
    required: true
    schema: {body_schema!r}
            """
        elif action == "delete":
            response_schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
            summary = f"Delete {meta.name}"
            params_yaml = """
  - name: id
    in: path
    type: integer
    required: true
    description: Record ID
            """
        else:
            response_schema = {"type": "object"}
            summary = f"{meta.name} {action}"

        # Flasgger uses YAML front-matter after a docstring line. Keep it minimal.
        yaml_doc = f'''{summary}
---
tags:
  - {tag}
parameters:{params_yaml if params_yaml.strip() else " []"}
responses:
  200:
    description: Successful operation
    schema: {response_schema!r}
    '''
        return yaml_doc

    @classmethod
    def _wrap_endpoint_for_flasgger(cls, endpoint_cls):
        """
        Turn a callable endpoint class into a plain function that:
        - forwards calls to the instance
        - carries __name__, __module__, and __doc__ for Flasgger
        """
        endpoint = endpoint_cls()

        def view(*args, **kwargs):
            return endpoint(*args, **kwargs)

        # make it look like a normal view function
        view.__name__ = endpoint_cls.__name__
        view.__qualname__ = endpoint_cls.__qualname__
        view.__module__ = endpoint_cls.__module__
        view.__doc__ = getattr(endpoint_cls, "__doc__", None)
        return view
