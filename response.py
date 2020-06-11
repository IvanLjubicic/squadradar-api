from flask import Response, jsonify

class ResponseGeneric(Response):
    @classmethod
    def force_type(cls, rv, environ=None):
        if isinstance(rv, dict):
            rv = jsonify(rv)
        return super(ResponseGeneric, cls).force_type(rv, environ)