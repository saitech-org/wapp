from .endpoint_base import WappEndpoint
from flask import request as flask_request

class WappModelEndpoint(WappEndpoint):
    model = None
    meta = None
    db = None

class Get(WappModelEndpoint):
    class Meta:
        method = 'GET'
        pattern = None  # Set dynamically
        name = None
        description = None
        request_model = None
        response_model = None

    def handle(self, request, query, path, body):
        obj = self.model.query.get(path.get('id'))
        if not obj:
            return self.to_response({"error": "Not found"}), 404
        return self.to_response(obj)

class List(WappModelEndpoint):
    class Meta:
        method = 'GET'
        pattern = None
        name = None
        description = None
        request_model = None
        response_model = None

    def handle(self, request, query, path, body):
        objs = self.model.query.all()
        return self.to_response(objs)

class Create(WappModelEndpoint):
    class Meta:
        method = 'POST'
        pattern = None
        name = None
        description = None
        request_model = None
        response_model = None

    def handle(self, request, query, path, body):
        data = body.model_dump() if body else (flask_request.get_json(silent=True) or {})
        obj = self.model(**data)
        self.db.session.add(obj)
        self.db.session.commit()
        return self.to_response(obj)

class Update(WappModelEndpoint):
    class Meta:
        method = 'PUT'
        pattern = None
        name = None
        description = None
        request_model = None
        response_model = None

    def handle(self, request, query, path, body):
        obj = self.model.query.get(path.get('id'))
        if not obj:
            return self.to_response({"error": "Not found"}), 404
        data = body.model_dump() if body else (flask_request.get_json(silent=True) or {})
        for k, v in data.items():
            setattr(obj, k, v)
        self.db.session.commit()
        return self.to_response(obj)

class Delete(WappModelEndpoint):
    class Meta:
        method = 'DELETE'
        pattern = None
        name = None
        description = None
        request_model = None
        response_model = None

    def handle(self, request, query, path, body):
        obj = self.model.query.get(path.get('id'))
        if not obj:
            return self.to_response({"error": "Not found"}), 404
        self.db.session.delete(obj)
        self.db.session.commit()
        return self.to_response({"deleted": True})
