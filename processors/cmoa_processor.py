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


def parse_cmoa_date(raw_val: Any, row: pd.Series) -> DateInfo:
    """
    Parse CMOA's date fields into a DateInfo object.

    The CSV provides:
      - creation_date (text like "1964-1965", "1999", "1984", etc.)
      - creation_date_earliest ("01/01/1964")
      - creation_date_latest ("01/01/1965")

    Strategy:
      1) If earliest == latest, treat as a single year (if parseable).
      2) Else, treat it as a range between earliest and latest years.
      3) If unparseable, fallback to UNKNOWN.

    We’re ignoring BCE in this example, but you can enhance if needed.
    """
    date_text = str(raw_val).strip()
    earliest = str(row.get("creation_date_earliest", "")).strip()
    latest = str(row.get("creation_date_latest", "")).strip()

    # Attempt to parse out just the year (last 4 digits) if date looks like mm/dd/yyyy
    def extract_year(yyyymmdd: str) -> Optional[int]:
        match = re.search(r'(\d{4})$', yyyymmdd)
        if match:
            return int(match.group(1))
        return None

    start_year = extract_year(earliest)
    end_year = extract_year(latest)

    # If no year info is found, mark as UNKNOWN
    if not start_year and not end_year:
        return DateInfo(
            type=DateType.UNKNOWN,
            display_text=date_text,
            start_year=None,
            end_year=None,
            is_bce=False
        )

    # If earliest and latest are the same, treat as single year
    if start_year and end_year and start_year == end_year:
        return DateInfo(
            type=DateType.YEAR,
            display_text=date_text,
            start_year=start_year,
            end_year=end_year,
            is_bce=False
        )

    # Otherwise, we have a range
    if start_year and end_year:
        # Ensure start <= end for CE
        # If out of order, swap or handle appropriately
        if end_year < start_year:
            start_year, end_year = end_year, start_year

        return DateInfo(
            type=DateType.YEAR_RANGE,
            display_text=date_text,
            start_year=start_year,
            end_year=end_year,
            is_bce=False
        )

    # If we only have one boundary, treat as a single year
    the_year = start_year or end_year
    return DateInfo(
        type=DateType.YEAR,
        display_text=date_text,
        start_year=the_year,
        end_year=the_year,
        is_bce=False
    )


def parse_cmoa_artist(raw_val: Any, row: pd.Series) -> Artist:
    """
    Parse artist info from multiple columns:
      - full_name (string)
      - birth_date / death_date (like '01/01/1947')

    We’ll extract the 4-digit year from those date strings for birth_year and death_year.
    If parsing fails or columns are missing, fall back to defaults.
    """
    full_name = str(row.get("full_name", "Unknown Artist")).strip()
    birth_date_str = str(row.get("birth_date", "")).strip()
    death_date_str = str(row.get("death_date", "")).strip()

    # Simple helper to extract the year from something like "01/01/1947"
    def extract_year(date_str: str) -> Optional[int]:
        match = re.search(r'(\d{4})$', date_str)
        if match:
            return int(match.group(1))
        return None

    birth_year = extract_year(birth_date_str)
    death_year = extract_year(death_date_str)

    return Artist(
        name=full_name if full_name else "Unknown Artist",
        birth_year=birth_year,
        death_year=death_year
    )


def parse_cmoa_images(raw_val: Any, row: pd.Series) -> list[Image]:
    """
    The CSV has a single 'image_url' column. We convert it to our standard list[Image].
    """
    if not raw_val or pd.isna(raw_val):
        return []
    return [Image(url=str(raw_val).strip(), copyright=None)]


class CarnegieMuseumDataProcessor(BaseMuseumDataProcessor):
    """
    Processor for Carnegie Museum of Art's open data.
    """

    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path, encoding='utf-8', low_memory=False)

    def get_museum_name(self) -> str:
        return "Carnegie Museum of Art"

    # Define how columns map to our UnifiedArtwork model
    column_map = {
        "id": {"model": "id"},
        "title": {"model": "object.name"},
        "creation_date": {"parse": parse_cmoa_date, "model": "object.creation_date"},
        # Treat 'medium' as our 'object.type'
        "medium": {"model": "object.type"},
        # URL to a single image
        "image_url": {"parse": parse_cmoa_images, "model": "images"},
        # Artist
        "full_name": {"parse": parse_cmoa_artist, "model": "artist"},
        # Use the museum’s web_url for artwork display
        "web_url": {"model": "web_url"},
    }

    # Any columns we don't want in metadata
    exclude_from_metadata = {
        "id",
        "title",
        "creation_date",
        "creation_date_earliest",
        "creation_date_latest",
        "medium",
        "image_url",
        "full_name",
        "web_url",
    }


if __name__ == "__main__":
    processor = CarnegieMuseumDataProcessor()
    data = processor.get_unified_data("../data/source_datasets/cmoa.csv")
    print(f"Processed {len(data)} artworks from CMOA.")
    for artwork in data[:3]:
        print(artwork.dict())
