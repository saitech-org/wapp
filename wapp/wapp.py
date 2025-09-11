from typing import List, Type

from django.db.models import Model as DjangoModel
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet
from django.urls import path

class Wapp:
    REGISTERED_WAPPS: List[Type["Wapp"]] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Register this Wapp subclass in the global registry
        Wapp.REGISTERED_WAPPS.append(cls)

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
    def urlpatterns(cls):
        router = DefaultRouter()
        models = getattr(cls, 'Models', None)
        if models:
            for name, model in models.__dict__.items():
                if Wapp._is_django_model(model):
                    slug = Wapp._get_model_slug(model)
                    viewset = Wapp._generate_viewset(model)
                    router.register(slug, viewset, basename=slug)
                    print(f"Registered model '{name}' with slug '{slug}' in router.")
        # Register custom endpoints from Endpoints class
        endpoints = getattr(cls, 'Endpoints', None)
        endpoint_patterns = []
        if endpoints:
            for name, view in endpoints.__dict__.items():
                if name.startswith('__'):
                    continue
                meta = getattr(view, '_wapp_endpoint_metadata', None)
                if meta and hasattr(meta, 'pattern') and hasattr(meta, 'name'):
                    endpoint_patterns.append(path(meta.pattern, view, name=meta.name))
        return list(router.urls) + endpoint_patterns

    @classmethod
    def urls(cls, app_name=None):
        if app_name is None:
            app_name = cls.__name__.lower()
        return cls.urlpatterns(), app_name
