from collections.abc import Callable
from typing import Type, Union, OrderedDict
from pydantic import BaseModel as PydanticModel
from django.db.models import Model as DjangoModel
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ModelSerializer

from wapp.decorators.endpoint_meta import EndpointMetadata
from wapp.decorators.model_meta import ModelMetadata

ModelType = Union[Type[PydanticModel], Type[DjangoModel]]

WappModels = OrderedDict[str, ModelType]

WappEndpoints = OrderedDict[Callable, EndpointMetadata]


class Wapp:
    def __init__(self, models: WappModels = None, endpoints: WappEndpoints = None):
        self.models = models or {}
        self.endpoints = endpoints or {}

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

    @property
    def urlpatterns(self):
        router = DefaultRouter()
        for name, model in self.models.items():
            if Wapp._is_django_model(model):
                slug = Wapp._get_model_slug(model)
                viewset = Wapp._generate_viewset(model)
                router.register(slug, viewset, basename=slug)
        return router.urls
