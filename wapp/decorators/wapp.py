from typing import Union

from wapp.decorators.endpoint_meta import EndpointMetadata
from wapp.decorators.model_meta import ModelMetadata


def wapp(metadata: Union[ModelMetadata, EndpointMetadata]):
    def decorator(obj):
        # If decorating a Django model and metadata is ModelMetadata, pass model_cls
        if isinstance(metadata, ModelMetadata):
            # If ModelMetadata was constructed without model_cls, reconstruct with model_cls
            if not hasattr(metadata, 'model_cls') or getattr(metadata, 'model_cls', None) is None:
                # Reconstruct ModelMetadata with model_cls=obj
                new_metadata = ModelMetadata(
                    slug=getattr(metadata, 'slug', None),
                    name=getattr(metadata, 'name', None),
                    name_plural=getattr(metadata, 'name_plural', None),
                    description=getattr(metadata, 'description', None),
                    icon=getattr(metadata, 'icon', None),
                    image_url=getattr(metadata, 'image_url', None),
                    model_cls=obj
                )
                setattr(obj, '_wapp_model_metadata', new_metadata)
            else:
                setattr(obj, '_wapp_model_metadata', metadata)
        elif isinstance(metadata, EndpointMetadata):
            setattr(obj, '_wapp_endpoint_metadata', metadata)
        return obj
    return decorator