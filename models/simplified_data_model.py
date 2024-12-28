from typing import Optional
from pydantic import BaseModel, HttpUrl


class Museum(BaseModel):
    """Model representing a museum."""
    name: str


class ArtObject(BaseModel):
    """Model representing an art object."""
    name: str
    creation_year: Optional[str]  # Date can be a freeform string for now
    type: Optional[str]  # e.g., painting, sculpture, etc.


class Artist(BaseModel):
    """Model representing an artist."""
    name: str  # Format: "Last Name, First Name"
    birth_year: Optional[int]
    death_year: Optional[int]


class Image(BaseModel):
    """Model representing an image associated with artwork."""
    url: Optional[HttpUrl]  # Ensures a valid URL if provided
    copyright: Optional[str]  # Copyright information


class UnifiedArtwork(BaseModel):
    """Model representing a unified artwork."""
    id: str  # Unique identifier
    museum: Museum  # Museum where the artwork is located
    object: ArtObject  # Art object information
    artist: Artist  # Artist information
    images: list[Image]  # List of images associated with the artwork
    web_url: Optional[HttpUrl]  # URL for viewing the artwork online
    metadata: dict  # Store all additional metadata as a dictionary (headers as keys, values as values for CSV)
