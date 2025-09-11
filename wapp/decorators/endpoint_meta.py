from typing import Optional


class EndpointMetadata:
    pattern: str  # URL pattern for the endpoint
    name: str  # Name of the endpoint
    description: Optional[str]  # Description of the endpoint

    def __init__(self,
                 pattern: str,
                 name: str,
                 description: Optional[str] = None):
        self.pattern = pattern
        self.name = name
        self.description = description