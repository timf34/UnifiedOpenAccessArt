from dataclasses import dataclass
from typing import Optional


# TODO: I still need to define this properly
@dataclass
class UnifiedArtworkData:
    id: str
    title: str
    artist: str
    date: Optional[str] = None
    medium: Optional[str] = None
    dimensions: Optional[str] = None
    credit_line: Optional[str] = None
    accession_number: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None