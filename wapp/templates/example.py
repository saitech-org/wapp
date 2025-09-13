from wapp.core import Wapp
from wapp.endpoint_base import WappEndpoint
from pydantic import BaseModel as PydanticModel
from app_env import db

class SomeEntity(db.Model):
    __tablename__ = 'owner'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)

    class WappModel:
        slug = "some_entity"
        name = "Some Entity"

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class OwnersWapp(Wapp):
    class Models:
        some_entity = SomeEntity
    class Endpoints:
        _some_entity = True  # auto CRUD

class CustomRequestModel(PydanticModel):
    name: str

class CustomResponseModel(PydanticModel):
    id: int
    name: str

class GetEntityByName(WappEndpoint):
    """Custom endpoint to get entity by name
    ---
    tags: [SomeEntity]
    responses:
      200:
        description: OK
    """
    class Meta:
        name = "Get Entity By Name"
        pattern = "/entity/by-name/<string:name>"
        method = "GET"
        request_model = CustomRequestModel  # No request body for GET
        response_model = CustomResponseModel

    def handle(self, request, query, path, body):
        entity = SomeEntity.query.filter_by(name=request.name).first()
        if entity:
            return entity.as_dict(), 200
        return {"message": "Entity not found"}, 404


class Example(Wapp):
    class Models:
        some_entity = SomeEntity
    class Endpoints:
        _some_entity = True  # auto CRUD
        get_entity_by_name = GetEntityByName