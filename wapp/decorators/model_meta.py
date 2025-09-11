from typing import Optional, Type


class ModelMetadata:
    slug: str  # Unique identifier for the model
    name: str  # Singular name of the model
    name_plural: Optional[str]  # Plural name of the model
    description: Optional[str]  # Description of the model
    icon: Optional[str]  # Icon representing the model
    image_url: Optional[str]  # URL to an image representing the model

    def __init__(self,
                 slug: Optional[str] = None,
                 name: Optional[str] = None,
                 name_plural: Optional[str] = None,
                 description: Optional[str] = None,
                 icon: Optional[str] = None,
                 image_url: Optional[str] = None,
                 model_cls: Optional[Type] = None):
        # If a Django model class is provided, fetch from _meta
        meta = getattr(model_cls, '_meta', None) if model_cls else None
        self.slug = slug or (getattr(meta, 'model_name', None) if meta else None)
        self.name = name or (getattr(meta, 'verbose_name', None) if meta else None)
        self.name_plural = name_plural or (getattr(meta, 'verbose_name_plural', None) if meta else None)
        self.description = description or (getattr(meta, 'description', None) if meta and hasattr(meta, 'description') else None)
        self.icon = icon
        self.image_url = image_url
        # Fallbacks if still missing
        if not self.slug and model_cls:
            self.slug = model_cls.__name__.lower()
        if not self.name and model_cls:
            self.name = model_cls.__name__
