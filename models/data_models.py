from enum import Enum
from typing import Optional
from pydantic import BaseModel, HttpUrl, model_validator


class DateType(Enum):
    YEAR = "year"  # Single year: "1889"
    YEAR_RANGE = "range"  # Range of years: "1980-1981"
    CENTURY = "century"  # Century: "15th century"
    UNKNOWN = "unknown"  # Unparseable or missing date


class DateInfo(BaseModel):
    """
    Simple parseable date representation.
    For BCE dates, years are stored as positive integers with is_bce=True
    rather than negative integers to make querying and display simpler.
    """
    type: DateType
    display_text: str  # Original text: "15th century", "1980-1981"
    start_year: Optional[int]  # Start year as positive integer
    end_year: Optional[int]  # End year as positive integer
    is_bce: bool = False  # Flag to indicate if the date is BCE

    @model_validator(mode="after")
    def validate_year_range(self):
        """Validate end_year is chronologically after start_year for YEAR_RANGE type."""
        if self.type == DateType.YEAR_RANGE and self.start_year is not None and self.end_year is not None:
            if self.is_bce:
                if self.end_year > self.start_year:
                    raise ValueError(
                        "For BCE dates, end_year must be chronologically later (smaller number) than start_year")
            elif self.end_year < self.start_year:
                raise ValueError("For CE dates, end_year must be >= start_year")
        return self


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
    url: Optional[HttpUrl] = None  # Ensures a valid URL if provided
    copyright: Optional[str] = None  # Copyright information


class UnifiedArtwork(BaseModel):
    """Model representing a unified artwork."""
    id: str  # Unique identifier
    museum: Museum  # Museum where the artwork is located
    object: ArtObject  # Art object information
    artist: Artist  # Artist information
    images: list[Image]  # List of images associated with the artwork
    web_url: Optional[HttpUrl]  # URL for viewing the artwork online
    metadata: dict  # Store all additional metadata as a dictionary (headers as keys, values as values for CSV); data dump for semantic or full text search
