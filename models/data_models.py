from enum import Enum
from typing import Optional
from pydantic import BaseModel, HttpUrl, field_validator, Field


class DateType(Enum):
    YEAR = "year"  # Single year: "1889"
    YEAR_RANGE = "range"  # Range of years: "1980-1981"
    CENTURY = "century"  # Century: "15th century"
    UNKNOWN = "unknown"  # Unparseable or missing date


class DateInfo(BaseModel):
    """Simple parseable date representation."""
    type: DateType
    display_text: str  # Original text: "15th century", "1980-1981"
    start_year: Optional[int]  # Start year, e.g., 1980 or 1400
    end_year: Optional[int]  # End year, e.g., 1981 or 1499

    @field_validator("end_year")
    @classmethod
    def validate_year_range(cls, end_year, values):
        start_year = values.get("start_year")
        date_type = values.get("type")
        if date_type == DateType.YEAR_RANGE and start_year is not None and end_year is not None:
            if end_year < start_year:
                raise ValueError("end_year must be greater than or equal to start_year")
        return end_year


class Museum(BaseModel):
    """Model representing a museum."""
    name: str


class ArtObject(BaseModel):
    """Model representing an art object."""
    name: str
    creation_date: Optional[DateInfo]
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
