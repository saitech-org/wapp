from typing import Optional


class ModelMetadata:
    slug: str  # Unique identifier for the model
    name: str  # Singular name of the model
    name_plural: Optional[str]  # Plural name of the model
    description: Optional[str]  # Description of the model
    icon: Optional[str]  # Icon representing the model
    image_url: Optional[str]  # URL to an image representing the model

    def __init__(self,
                 slug: str,
                 name: str,
                 name_plural: Optional[str] = None,
                 description: Optional[str] = None,
                 icon: Optional[str] = None,
                 image_url: Optional[str] = None):
        self.slug = slug
        self.name = name
        self.name_plural = name_plural
        self.description = description
        self.icon = icon
        self.image_url = image_url
