import logging
from flask import jsonify, request as flask_request


class WappEndpoint:
    class Meta:
        method = None
        pattern = None
        name = None
        description = None
        request_model = None
        response_model = None

    def __call__(self, *args, **kwargs):
        return self.handle_request(*args, **kwargs)

    def handle_request(self, *args, **kwargs):
        try:
            # Query params
            query = dict(flask_request.args)
            # Path params
            path = kwargs
            # Request body
            body = None
            if self.Meta.request_model:
                try:
                    data = flask_request.get_json(force=True, silent=True) or {}
                    body = self.Meta.request_model.model_validate(data)
                except Exception:
                    body = None
            # Call user handler
            return self.handle(flask_request, query, path, body)
        except Exception as e:
            logging.exception(f"Error in {self.__class__.__name__}: {e}")
            return jsonify({"error": str(e)}), 500

    def handle(self, request, query, path, body):
        raise NotImplementedError("Endpoint must implement handle() method.")

    def to_response(self, data):
        if hasattr(data, "as_dict"):
            return jsonify(data.as_dict())
        if isinstance(data, list) and data and hasattr(data[0], "as_dict"):
            return jsonify([item.as_dict() for item in data])
        return jsonify(data)

    def __repr__(self):
        return f"<{self.__class__.__name__} {getattr(self.Meta, 'name', '')}>"
