from django.db import models
from wapp.decorators.wapp import wapp
from wapp.decorators.model_meta import ModelMetadata
from wapp.wapp import Wapp

@wapp(ModelMetadata(
    slug="thing"
))
class Thing(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Thing"
        verbose_name_plural = "Things"


class ThingsWapp(Wapp):
    class Models:
        thing = Thing