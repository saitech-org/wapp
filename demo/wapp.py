from env import db
import pydantic
from wapp.core import Wapp
from wapp.endpoint_base import WappEndpoint
import random
import string


class Foo(db.Model):
    __tablename__ = 'foo'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    bat = db.Column(db.JSON, nullable=True)  # New JSON/dict field
    ok = db.Column(db.Boolean, default=True)  # New Boolean field

    class WappModel:
        slug = "foo"
        name = "Foo"
        description = "A model representing a Foo entity"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Bar(db.Model):
    __tablename__ = 'bar'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=True)

    class WappModel:
        slug = "bar"
        name = "Bar"
        name_plural = "Bars"
        description = "A model representing a Bar entity"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class RequestModel(pydantic.BaseModel):
    param1: str
    param2: int


class ResponseModel(pydantic.BaseModel):
    result1: str
    result2: int


class HandleRequest(WappEndpoint):
    class Meta:
        pattern = "/handle/"
        method = "PUT"
        name = "HandleRequest"
        description = "An endpoint to handle requests"
        request_model = RequestModel
        response_model = ResponseModel

    def handle(self, request, query, path, body):
        if body is None:
            return self.to_response({"error": "Invalid request body"}), 400
        resp = self.Meta.response_model(result1=f"Handled {body.param1}", result2=body.param2)
        return self.to_response(resp.model_dump())


class CreateRandomFoo(WappEndpoint):
    class Meta:
        pattern = "/foo/random/"
        method = "GET"
        name = "CreateRandomFoo"
        description = "Create a random Foo and return it."
        request_model = None
        response_model = None

    def handle(self, request, query, path, body):
        name = ''.join(random.choices(string.ascii_letters, k=8))
        description = 'Random description: ' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        bat = {"random": random.randint(1, 100)}
        foo = Foo(name=name, description=description, bat=bat)
        db.session.add(foo)
        db.session.commit()
        return self.to_response(foo)


class DemoWapp(Wapp):
    class Models:
        foo = Foo
        bar = Bar

    class Endpoints:
        handle = HandleRequest
        create_random_foo = CreateRandomFoo
        _foo = True
        _bar = ["list", "get"]
