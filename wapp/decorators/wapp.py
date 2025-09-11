from typing import Union

from wapp.decorators.endpoint_meta import EndpointMetadata
from wapp.decorators.model_meta import ModelMetadata


def wapp(metadata:Union[ModelMetadata, EndpointMetadata]):
    def decorator(obj):
        if isinstance(metadata, ModelMetadata):
            setattr(obj, '_wapp_model_metadata', metadata)
        elif isinstance(metadata, EndpointMetadata):
            setattr(obj, '_wapp_endpoint_metadata', metadata)
        return obj
    return decorator