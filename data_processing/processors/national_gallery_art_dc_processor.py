import pandas as pd
from typing import Any

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import (
    DateInfo,
    DateType,
    Artist,
    Image,
    UnifiedArtwork
)


def parse_nga_date(raw_val: Any, row: pd.Series) -> DateInfo:
    """
    Parse NGA date formats into a DateInfo object.
    Uses displaydate for display_text, and beginyear/endyear for actual years.
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
    if begin_year is not None and end_year is not None and begin_year != end_year:
        return DateInfo(
            type=DateType.YEAR_RANGE,
            display_text=display_text,
            start_year=begin_year,
            end_year=end_year
        )

    # If we have at least one year, use it as a single year
    year = begin_year if begin_year is not None else end_year
    if year is not None:
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
    Parse artist information from attribution field.
    Returns Artist with just the name, as birth/death years aren't provided.
    """
    if not raw_val or pd.isna(raw_val):
        return Artist(name="Unknown Artist", birth_year=None, death_year=None)

    return Artist(
        name=str(raw_val).strip(),
        birth_year=None,
        death_year=None
    )


def parse_nga_images(raw_val: Any, row: pd.Series) -> list[Image]:
    """
    Currently no image URLs in the sample data.
    This is a placeholder for when image data becomes available.
    """
    return []


def parse_nga_web_url(raw_val: Any, row: pd.Series) -> str:
    """
    Generate the URL using the objectid. The `raw_val` is not used directly;
    we rely on row['objectid'] instead.
    """
    object_id = row.get("objectid")
    if pd.notna(object_id):
        return f"https://www.nga.gov/collection/art-object-page.{object_id}.html"
    return ""


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
        "medium": {"model": "object.type"},
        "attribution": {"parse": parse_nga_artist, "model": "artist"},
    }

    # Columns to exclude from metadata
    exclude_from_metadata = {
        "objectid",
        "title",
        "displaydate",
        "beginyear",
        "endyear",
        "medium",
        "attribution",
        "attributioninverted",
        "url"
    }

    # Overriding
    def _row_to_artwork(self, row: pd.Series, index) -> UnifiedArtwork:
        # Let the base processor do the heavy lifting first
        artwork = super()._row_to_artwork(row, index)

        # Now, create the web_url from objectid, even if 'url' column doesn't exist.
        object_id = row.get("objectid")
        if pd.notna(object_id):
            artwork.web_url = f"https://www.nga.gov/collection/art-object-page.{object_id}.html"

        return artwork


if __name__ == "__main__":
    processor = NGADataProcessor()
    data = processor.get_unified_data("../../data/source_datasets/national_gallery_of_art_dc.csv", dev_mode=True)
    print(f"Processed {len(data)} artworks from NGA.")
    for artwork in data[:3]:
        print(artwork.dict())
