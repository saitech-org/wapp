from django.db.models import Model as DjangoModel
from rest_framework.routers import DefaultRouter
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet


class Wapp:
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
        if not models:
            return []

        for name, model in models.__dict__.items():
            if Wapp._is_django_model(model):
                print(f'Registering model: {name}')
                slug = Wapp._get_model_slug(model)
                viewset = Wapp._generate_viewset(model)
                router.register(slug, viewset, basename=slug)
        return router.urls

    @classmethod
    def urls(cls, app_name=None):
        if app_name is None:
            app_name = cls.__name__.lower()
        return (cls.urlpatterns(), app_name)