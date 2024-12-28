import pandas as pd
import re
from typing import Any

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import DateInfo, DateType, Artist, Image


def parse_date(raw_val: Any, row: pd.Series) -> DateInfo:
    """
    Example date parser for Cleveland:
    - raw_val might be '1902'
    - We also look at row['creation_date_earliest'], row['creation_date_latest'], etc.
    """
    # Simple example: if raw_val is 'c. 1895', just extract a 4-digit year
    # In practice, you might replicate the logic from your current code.
    match = re.search(r'(\d{4})', str(raw_val))
    year = int(match[1]) if match else None
    if year:
        return DateInfo(type=DateType.YEAR, display_text=str(raw_val), start_year=year, end_year=year)
    else:
        return DateInfo(type=DateType.UNKNOWN, display_text=str(raw_val), start_year=None, end_year=None)


def parse_creators(raw_val: Any, row: pd.Series) -> Artist:
    """
    Example for Cleveland's 'creators' field, returning an Artist object.
    """
    if not raw_val or pd.isna(raw_val):
        return Artist(name="Unknown Artist", birth_year=None, death_year=None)
    # Just take the first part
    main_creator = re.split(r';|,', str(raw_val))[0].strip()
    # Remove parentheses
    main_creator = re.sub(r'\([^)]*\)', '', main_creator).strip()
    return Artist(name=main_creator, birth_year=None, death_year=None)


def parse_images(raw_val: Any, row: pd.Series) -> list[Image]:
    """
    Cleveland has 3 columns: image_web, image_print, image_full
    But here, each column is separate so we might just parse them individually.
    For demonstration, assume raw_val is always an image URL.
    """
    if pd.isna(raw_val):
        return []
    return [Image(url=str(raw_val))]


class ClevelandMuseumDataProcessor(BaseMuseumDataProcessor):
    # Our base class will call load_data, so define it
    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path, encoding='utf-8', low_memory=False)

    def get_museum_name(self) -> str:
        return "Cleveland Museum of Art"

    # Here’s where we define the column mapping
    column_map = {
        "id": {"model": "id"},  # store raw ID directly into 'artwork.id'
        "title": {"model": "object.name"},
        "type": {"model": "object.type"},
        "creation_date": {"parse": parse_date, "model": "object.creation_date"},
        "creators": {"parse": parse_creators, "model": "artist"},
        "image_web": {"parse": parse_images, "model": "images"},
        "image_print": {"parse": parse_images, "model": "images"},
        "url": {"model": "web_url"},
    }

    exclude_from_metadata = {
        "id", "title", "type", "creation_date",
        "creators", "image_web", "image_print", "image_full", "url"
    }


if __name__ == "__main__":
    processor = ClevelandMuseumDataProcessor()
    data = processor.get_unified_data("../data/source_datasets/cleveland_museum_of_art.csv")
    print(f"Processed {len(data)} artworks.")
    for artwork in data[:3]:
        print(artwork.dict())