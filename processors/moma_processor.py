import pandas as pd
import re
from typing import Any, Optional, List

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


def parse_moma_date(raw_val: Any, row: pd.Series) -> DateInfo:
    """
    Parse MOMA's date formats into a DateInfo object.

    Examples:
    - "1896" -> Single year
    - "1903" -> Single year
    - "1980" -> Single year

    Note: MOMA uses negative years to indicate BCE dates in BeginDate/EndDate
    for artist lifespans, but artwork dates appear to be CE.
    """
    if not raw_val or pd.isna(raw_val):
        return DateInfo(
            type=DateType.UNKNOWN,
            display_text="",
            start_year=None,
            end_year=None
        )

    date_str = str(raw_val).strip()

    # Try to extract a 4-digit year
    year_match = re.search(r'(\d{4})', date_str)
    if year_match:
        year = int(year_match.group(1))
        return DateInfo(
            type=DateType.YEAR,
            display_text=date_str,
            start_year=year,
            end_year=year,
            is_bce=False
        )

    # If no year found, return unknown
    return DateInfo(
        type=DateType.UNKNOWN,
        display_text=date_str,
        start_year=None,
        end_year=None
    )


def parse_moma_artist(raw_val: Any, row: pd.Series) -> Artist:
    """
    Parse MOMA's artist information from multiple columns:
    - Artist (name)
    - ArtistBio (contains nationality and life dates in parentheses)
    - BeginDate/EndDate (birth/death years with parentheses)

    Examples:
    Artist: "Otto Wagner"
    ArtistBio: "(Austrian, 1841–1918)"
    BeginDate: "(1841)"
    EndDate: "(1918)"
    """
    if not raw_val or pd.isna(raw_val):
        return Artist(name="Unknown Artist", birth_year=None, death_year=None)

    # Get the basic name
    name = str(raw_val).strip()

    # Extract birth and death years from BeginDate/EndDate
    birth_year = None
    death_year = None

    try:
        begin_date = row.get('BeginDate')
        if begin_date and pd.notna(begin_date):
            # Extract number from parentheses
            year_match = re.search(r'\((\d{4})\)', str(begin_date))
            if year_match:
                birth_year = int(year_match.group(1))
    except (ValueError, TypeError):
        pass

    try:
        end_date = row.get('EndDate')
        if end_date and pd.notna(end_date):
            # Extract number from parentheses
            year_match = re.search(r'\((\d{4})\)', str(end_date))
            if year_match:
                death_year = int(year_match.group(1))
    except (ValueError, TypeError):
        pass

    return Artist(
        name=name,
        birth_year=birth_year,
        death_year=death_year
    )


def parse_moma_images(raw_val: Any, row: pd.Series) -> list[Image]:
    """
    Parse MOMA's image URLs.
    ImageURL column contains full URLs to images.
    """
    if not raw_val or pd.isna(raw_val):
        return []

    return [Image(
        url=str(raw_val).strip(),
        copyright=None  # MOMA doesn't provide explicit copyright info in the CSV
    )]


class MoMADataProcessor(BaseMuseumDataProcessor):
    """
    Processor for Museum of Modern Art (MoMA) open data.
    """

    def load_data(self, file_path: str, dev_mode: bool = False) -> pd.DataFrame:
        nrows = self.DEV_MODE_ROWS if dev_mode else None
        return pd.read_csv(file_path, encoding='utf-8', low_memory=False, nrows=nrows)

    def get_museum_name(self) -> str:
        return "Museum of Modern Art"

    # Define how columns map to our UnifiedArtwork model
    column_map = {
        "ObjectID": {"model": "id"},
        "Title": {"model": "object.name"},
        "Date": {"parse": parse_moma_date, "model": "object.creation_date"},
        "Classification": {"model": "object.type"},
        "Artist": {"parse": parse_moma_artist, "model": "artist"},
        "ImageURL": {"parse": parse_moma_images, "model": "images"},
        "URL": {"model": "web_url"},
    }

    # Columns we don't want in metadata
    exclude_from_metadata = {
        "ObjectID",
        "Title",
        "Date",
        "Classification",
        "Artist",
        "ImageURL",
        "URL",
        "BeginDate",
        "EndDate",
        "ArtistBio"
    }


if __name__ == "__main__":
    processor = MoMADataProcessor()
    data = processor.get_unified_data("../data/source_datasets/moma.csv", dev_mode=True)
    print(f"Processed {len(data)} artworks from MoMA.")
    for artwork in data[:3]:
        print(artwork.dict())