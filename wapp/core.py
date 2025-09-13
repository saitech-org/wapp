from typing import List, Tuple, Type

from flask import Blueprint
from sqlalchemy.orm import DeclarativeMeta
from inspect import isclass
from .endpoint_base import WappEndpoint

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
        Binds the db, computes endpoints, creates blueprint, and registers it with the Flask app.
        """
        cls._cached_endpoints = None  # Reset cache in case of rebind
        cls._blueprint = None
        cls.bind_db(db_instance)
        cls.get_endpoints(fresh=True)  # Compute and cache endpoints
        cls._blueprint = cls._create_blueprint(url_prefix=url_prefix)
        app.register_blueprint(cls._blueprint)
        # Bind nested wapps recursively
        for _, wapp in cls.get_wapps():
            wapp.bind(app, db_instance, url_prefix=f"/{wapp.name}")

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
    def _create_blueprint(cls, url_prefix=None, parent_prefix=""):
        this_prefix = url_prefix or ""
        full_prefix = (parent_prefix.rstrip("/") + this_prefix).replace("//", "/")
        bp = Blueprint(cls.__name__, __name__, url_prefix=this_prefix)
        for name, endpoint_cls in cls.get_endpoints():
            meta = getattr(endpoint_cls, 'Meta', None)
            if meta and meta.pattern and meta.method:
                endpoint_instance = endpoint_cls()
                # Use blueprint name, module, and qualname for global uniqueness
                endpoint_name = f"{bp.name}_{endpoint_cls.__module__}__{endpoint_cls.__qualname__}".replace(".", "_")
                api_path = (full_prefix.rstrip("/") + meta.pattern).replace("//", "/")
                print(f"Registering endpoint: {meta.method} {api_path} -> {endpoint_cls.__name__} ({meta.name}) as {endpoint_name}")
                bp.add_url_rule(
                    meta.pattern,
                    endpoint=endpoint_name,
                    view_func=endpoint_instance,
                    methods=[meta.method]
                )
        for wapp_name, wapp_cls in cls.get_wapps():
            nested_prefix = f"{full_prefix}/{wapp_name}".replace("//", "/")
            nested_bp = wapp_cls._create_blueprint(url_prefix=f"/{wapp_name}", parent_prefix=full_prefix)
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
                        if v is False:
                            continue  # Explicitly disabled
                        if v and isclass(v) and issubclass(v, WappEndpoint):
                            result.append((f"{model_name}_{action}", v))
                            to_set[f"{model_name}_{action}"] = v
                        elif v is None:
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
        # Dynamically create a subclass and bind model/meta/db
        class_attrs = {
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
