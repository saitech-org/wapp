from django.db import models
from wapp.wapp import Wapp
from wapp.db_models import BaseModelWithTimestamps
from wapp.decorators.model_meta import ModelMetadata
from wapp.decorators.wapp import wapp



@wapp(ModelMetadata(
    slug="foo",
    name="Foo",
    name_plural= "",
    description="A model representing a Foo entity",
))
class Foo(BaseModelWithTimestamps):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

@wapp(ModelMetadata(
    slug="bar",
    name="Bar",
    name_plural="Bars",
    description="A model representing a Bar entity",
))
class Bar(BaseModelWithTimestamps):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    content = models.TextField(null=True, blank=True)


class DemoWapp(Wapp):
    class Models:
        foo = Foo
        bar = Bar
