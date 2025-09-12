from inspect import isclass

from django.db.models import Model as DjangoModel
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet
from django.urls import path, include


class Wapp:
    @classmethod
    def get_models(cls) -> list[tuple[str, type[DjangoModel]]]:
        models = getattr(cls, 'Models', None)
        if not models:
            return []

        return [
            (name, model)
            for name, model in models.__dict__.items() if Wapp._is_django_model(model)
        ]

    @classmethod
    def get_endpoints(cls):
        endpoints = getattr(cls, 'Endpoints', None)
        if not endpoints:
            return []

        return [
            (name, view)
            for name, view in endpoints.__dict__.items() if not name.startswith('__')
        ]

    @classmethod
    def get_wapps(cls) -> list[tuple[str, type['Wapp']]]:
        wapps = getattr(cls, 'Wapps', None)
        if not wapps:
            return []

        return [
            (name, wapp)
            for name, wapp in wapps.__dict__.items()
            if isclass(wapp) and issubclass(wapp, Wapp) and wapp is not cls
        ]

    @staticmethod
    def _is_django_model(model):
        try:
            return issubclass(model, DjangoModel)
        except Exception:
            return False

    @staticmethod
    def _get_model_slug(model):
        meta = getattr(model, '__wapp_model_meta__', None)
        if meta and hasattr(meta, 'slug'):
            return meta.slug
        return model.__name__.lower()

    @staticmethod
    def _generate_serializer(model):
        meta_class = type('Meta', (), {'model': model, 'fields': '__all__'})
        serializer_class = type(f'{model.__name__}AutoSerializer', (ModelSerializer,), {'Meta': meta_class})
        return serializer_class

    @staticmethod
    def _generate_viewset(model):
        serializer = Wapp._generate_serializer(model)
        viewset = type(f'{model.__name__}ViewSet', (ModelViewSet,), {
            'queryset': model.objects.all(),
            'serializer_class': serializer
        })
        return viewset

    @classmethod
    def urlpatterns(cls, prefix=""):
        router = DefaultRouter()
        models = cls.get_models()
        for name, model in models:
            if Wapp._is_django_model(model):
                model_slug = Wapp._get_model_slug(model)
                viewset = Wapp._generate_viewset(model)
                print(f"[Wapp Mapping] Wapp: {cls.__name__}, Model: {name} ({model.__module__}.{model.__name__}), Slug: {model_slug}")
                router.register(model_slug, viewset, basename=model_slug)

        patterns = []
        app_name = getattr(cls, 'WAPP_LABEL', cls.__name__.lower())
        # Always include router under prefix (even if empty)
        if list(router.urls):
            if prefix:
                patterns.append(path(f"{prefix}", include((router.urls, app_name))))
            else:
                patterns.append(path("", include((router.urls, app_name))))

        # Custom endpoints (if any)
        endpoints = getattr(cls, 'Endpoints', None)
        if endpoints:
            for name, view in endpoints.__dict__.items():
                if name.startswith('__'):
                    continue
                meta = getattr(view, '_wapp_endpoint_metadata', None)
                if meta and hasattr(meta, 'pattern') and hasattr(meta, 'name'):
                    if prefix:
                        patterns.append(path(f"{prefix}{meta.pattern}", view, name=meta.name))
                    else:
                        patterns.append(path(meta.pattern, view, name=meta.name))

        # Nested Wapps
        for app_path, nested_cls in cls.get_wapps():
            nested_prefix = f"{prefix}{app_path}/" if prefix else f"{app_path}/"
            patterns.append(path(nested_prefix, include(nested_cls.urls())))

        # Log all registered urlpatterns for this Wapp
        print(f"[Wapp URLPatterns] Wapp: {cls.__name__}, Prefix: '{prefix}'")
        for pattern in patterns:
            route = getattr(getattr(pattern, 'pattern', None), '_route', None)
            callback = getattr(pattern, 'callback', None)
            print(f"  - {route or pattern}: {callback}")
        return patterns

    @classmethod
    def urls(cls, app_name=None):
        if app_name is None:
            app_name = getattr(cls, 'WAPP_LABEL', cls.__name__.lower())
        return cls.urlpatterns(prefix=""), app_name
