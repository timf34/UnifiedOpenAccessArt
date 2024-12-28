import pandas as pd
import re
from typing import Any, Optional

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import (
    DateInfo,
    DateType,
    Artist,
    Image,
    UnifiedArtwork,
    ArtObject,
    Museum
)


def parse_nga_date(raw_val: Any, row: pd.Series) -> DateInfo:
    """
    Parse NGA date formats into a DateInfo object.
    Uses displaydate, beginyear, and endyear fields.

    Examples:
    - displaydate: "1430s", beginyear: 1430, endyear: 1440 -> YEAR_RANGE
    - displaydate: "c. 1310", beginyear: 1310, endyear: 1310 -> YEAR
    - displaydate: "1333", beginyear: 1333, endyear: 1333 -> YEAR
    """
    display_text = str(raw_val) if pd.notna(raw_val) else ""
    begin_year = row.get('beginyear')
    end_year = row.get('endyear')

    # Handle missing/invalid dates
    if pd.isna(begin_year) and pd.isna(end_year):
        return DateInfo(
            type=DateType.UNKNOWN,
            display_text=display_text,
            start_year=None,
            end_year=None
        )

    # Convert to integers, handling NaN values
    try:
        begin_year = int(begin_year) if pd.notna(begin_year) else None
        end_year = int(end_year) if pd.notna(end_year) else None
    except (ValueError, TypeError):
        return DateInfo(
            type=DateType.UNKNOWN,
            display_text=display_text,
            start_year=None,
            end_year=None
        )

    # If we have both years and they're different, it's a range
    if begin_year and end_year and begin_year != end_year:
        return DateInfo(
            type=DateType.YEAR_RANGE,
            display_text=display_text,
            start_year=begin_year,
            end_year=end_year
        )

    # If we have at least one year, use it as a single year
    year = begin_year or end_year
    if year:
        return DateInfo(
            type=DateType.YEAR,
            display_text=display_text,
            start_year=year,
            end_year=year
        )

    return DateInfo(
        type=DateType.UNKNOWN,
        display_text=display_text,
        start_year=None,
        end_year=None
    )


def parse_nga_artist(raw_val: Any, row: pd.Series) -> Artist:
    """
    Parse artist information from attribution fields.
    Uses both attribution and attributioninverted fields if available.

    The attributioninverted field typically has "Last Name, First Name" format
    while attribution has "First Name Last Name" format.
    We'll prefer attributioninverted when available.
    """
    if not raw_val or pd.isna(raw_val):
        return Artist(name="Unknown Artist", birth_year=None, death_year=None)

    # Try to get the inverted attribution first (Last Name, First Name format)
    inverted = row.get('attributioninverted')
    if inverted and pd.notna(inverted):
        name = str(inverted).strip()
    else:
        name = str(raw_val).strip()

    # Look for years in parentheses at the end of either attribution
    # For example: "Artist Name (1500-1570)"
    years_match = re.search(r'\((\d{4})-(\d{4})\)', str(raw_val))
    birth_year = None
    death_year = None

    if years_match:
        try:
            birth_year = int(years_match.group(1))
            death_year = int(years_match.group(2))
        except (ValueError, TypeError):
            pass

    return Artist(
        name=name,
        birth_year=birth_year,
        death_year=death_year
    )


def parse_nga_images(raw_val: Any, row: pd.Series) -> list[Image]:
    """
    Parse image information from customprinturl.
    Note: The actual NGA might require constructing image URLs differently
    or using additional API endpoints. This is a simplified version.
    """
    if not raw_val or pd.isna(raw_val):
        return []

    url = str(raw_val).strip()
    if not url:
        return []

    # Add image with no copyright info (could be enhanced with actual rights info)
    return [Image(url=url, copyright=None)]


class NGADataProcessor(BaseMuseumDataProcessor):
    """
    Processor for National Gallery of Art (DC) open data.
    """

    def load_data(self, file_path: str, dev_mode: bool = False) -> pd.DataFrame:
        nrows = self.DEV_MODE_ROWS if dev_mode else None
        return pd.read_csv(file_path, encoding='utf-8', low_memory=False, nrows=nrows)

    def get_museum_name(self) -> str:
        return "National Gallery of Art"

    # Define column mapping
    column_map = {
        "objectid": {"model": "id"},
        "title": {"model": "object.name"},
        "displaydate": {"parse": parse_nga_date, "model": "object.creation_date"},
        "classification": {"model": "object.type"},
        "attribution": {"parse": parse_nga_artist, "model": "artist"},
        "customprinturl": {"parse": parse_nga_images, "model": "images"},
        "wikidataid": {"model": "web_url"}  # Using Wikidata ID as a fallback URL
    }

    # Columns to exclude from metadata
    exclude_from_metadata = {
        "objectid",
        "title",
        "displaydate",
        "beginyear",
        "endyear",
        "classification",
        "attribution",
        "attributioninverted",
        "customprinturl",
        "wikidataid"
    }


if __name__ == "__main__":
    processor = NGADataProcessor()
    data = processor.get_unified_data("../data/source_datasets/national_gallery_of_art_dc.csv", dev_mode=True)
    print(f"Processed {len(data)} artworks from NGA.")
    for artwork in data[:3]:
        print(artwork.dict())