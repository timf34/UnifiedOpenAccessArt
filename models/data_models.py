"""
When flattening this to a CSV file, we'll need to flatten the nested fields.

TODO: have a museum field and date of museum dataset
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date


class Artist(BaseModel):
    name: str
    birth_date: Optional[str]
    death_date: Optional[str]
    nationality: Optional[str]
    biography: Optional[str]
    role: Optional[str]


class Dimension(BaseModel):
    value: float
    unit: str
    type: str  # e.g., "height", "width", "depth", "diameter"


class Image(BaseModel):
    url: Optional[str]
    copyright: Optional[str]
    type: Optional[str]  # e.g., "primary", "alternate", "detail"


class ArtworkLocation(BaseModel):
    gallery: Optional[str]
    room: Optional[str]
    wall: Optional[str]
    current_location: Optional[str]


class Provenance(BaseModel):
    description: str
    date: Optional[date]


class UnifiedArtwork(BaseModel):
    id: str  # Required
    accession_number: str  # Required
    title: str  # Required
    artist: Artist  # Required
    date_created: Optional[str]  # TODO, what even are these dates?
    date_start: Optional[int]  # Optional
    date_end: Optional[int]  # Optional
    medium: Optional[str]  # Optional
    dimensions: List[Dimension] = []  # Defaults to an empty list if missing
    credit_line: Optional[str] = None  # TODO: who cares about this? Optional, defaults to None
    department: Optional[str] = None  # Optional, defaults to None
    classification: Optional[str] = None
    object_type: Optional[str] = None
    culture: Optional[str] = None
    period: Optional[str] = None
    dynasty: Optional[str] = None
    provenance: List[Provenance] = []  # Defaults to an empty list if missing
    description: Optional[str] = None
    exhibition_history: Optional[str] = None
    bibliography: Optional[str] = None
    images: List[Image] = []  # Defaults to an empty list if missing
    is_public_domain: bool = False  # Defaults to False if missing
    rights_and_reproduction: Optional[str] = None
    location: Optional[ArtworkLocation] = None
    url: Optional[str] = None

    source_museum: str  # Required
    original_metadata: dict = Field(default_factory=dict)  # Defaults to an empty dict


    class Config:
        allow_population_by_field_name = True