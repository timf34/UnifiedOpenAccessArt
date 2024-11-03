"""
When flattening this to a CSV file, we'll need to flatten the nested fields.

TODO: have a musem field and date of museum dataset
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
    id: str
    accession_number: str
    title: str
    artist: Artist
    date_created: Optional[str]
    date_start: Optional[int]
    date_end: Optional[int]
    medium: Optional[str]
    dimensions: List[Dimension]
    credit_line: Optional[str]
    department: Optional[str]
    classification: Optional[str]
    object_type: Optional[str]
    culture: Optional[str]
    period: Optional[str]
    dynasty: Optional[str]
    provenance: List[Provenance] = []
    description: Optional[str]
    exhibition_history: Optional[str]
    bibliography: Optional[str]
    images: List[Image] = []
    is_public_domain: bool = False
    rights_and_reproduction: Optional[str]
    location: Optional[ArtworkLocation]
    url: Optional[str]

    # Museum-specific fields
    source_museum: str
    original_metadata: dict = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True