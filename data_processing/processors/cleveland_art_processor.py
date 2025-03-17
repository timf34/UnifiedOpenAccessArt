"""
Note: it took about 3 hours to write this and get it working 100% correctly.
The rest should be easier!
"""

import pandas as pd
import re
from typing import Any
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

from data_processing.processors.base_processor import BaseMuseumDataProcessor
from models.data_models import DateInfo, DateType, Artist, Image


def parse_date(raw_val: Any, row: pd.Series) -> DateInfo:
    """
    Parses various date formats and returns a DateInfo object.
    Handles both CE and BCE dates, and abbreviated year ranges.

    Examples:
    - 'c. 1846–83' -> type: YEAR_RANGE, start_year: 1846, end_year: 1883, is_bce: False
    - '1000–900 BCE' -> type: YEAR_RANGE, start_year: 1000, end_year: 900, is_bce: True
    - '2454-2311 BCE' -> type: YEAR_RANGE, start_year: 2454, end_year: 2311, is_bce: True
    - '1980-1' -> type: YEAR_RANGE, start_year: 1980, end_year: 1981, is_bce: False
    """
    date_str = str(raw_val).lower()

    # Handle unknown or unparseable dates
    if 'unknown' in date_str or not re.search(r'\d', date_str):
        return DateInfo(type=DateType.UNKNOWN, display_text=str(raw_val), start_year=None, end_year=None)

    # Check if it's BCE
    is_bce = 'bce' in date_str or 'b.c.' in date_str

    # First try to find full year range with potentially abbreviated second year
    range_match = re.search(r'(\d+)[-–]\s*(\d+)', date_str)
    if range_match:
        start = range_match.group(1)
        end = range_match.group(2)

        # For BCE dates, treat all numbers as full years
        if is_bce:
            start_year = int(start)
            end_year = int(end)
        else:
            # For CE dates, handle abbreviated years
            start_year = int(start)
            if len(end) == 1:
                # Handle single digit abbreviation (e.g., "1980-1" -> 1981)
                end_year = start_year + 1
            elif len(end) == 2:
                end_year = int(f"{start_year // 100}{end}")
                # If end year is less than start year, it's probably in the next century
                if end_year < start_year:
                    end_year += 100
            else:
                end_year = int(end)

        return DateInfo(
            type=DateType.YEAR_RANGE,
            display_text=str(raw_val),
            start_year=start_year,
            is_bce=is_bce,
            end_year=end_year,
        )

    # Extract all 4-digit years
    years = re.findall(r'(\d{4})', date_str)
    if not years:
        return DateInfo(type=DateType.UNKNOWN, display_text=str(raw_val), start_year=None, end_year=None)

    # Convert extracted years to integers, keeping them positive
    years = [int(year) for year in years]
    if not is_bce:
        years.sort()
    else:
        years.sort(reverse=True)  # For BCE, we want larger numbers first

    # Single year or full range
    if len(years) > 1:
        return DateInfo(
            type=DateType.YEAR_RANGE,
            display_text=str(raw_val),
            start_year=years[0],
            is_bce=is_bce,
            end_year=years[-1],
        )
    else:
        return DateInfo(
            type=DateType.YEAR,
            display_text=str(raw_val),
            start_year=years[0],
            is_bce=is_bce,
            end_year=years[0],
        )

def parse_creators(raw_val: Any, row: pd.Series) -> Artist:
    """
    Example for Cleveland's 'creators' field, returning an Artist object.
    Extracts name, birth year, and death year from strings like:
    - "Camille Pissarro (French, 1830–1903), artist"
    - "Albert-Charles Lebourg (French, 1849–1928), artist"
    """
    if not raw_val or pd.isna(raw_val):
        return Artist(name="Unknown Artist", birth_year=None, death_year=None)

    # Just take the first part before semicolon or comma if multiple creators
    main_creator = re.split(r';|,\s*(?:artist|painter|sculptor)', str(raw_val))[0].strip()

    # Try to extract birth and death years
    birth_year = None
    death_year = None
    years_match = re.search(r'\(.*?,\s*(\d{4})[-–](\d{4})\)', main_creator)
    if years_match:
        birth_year = int(years_match.group(1))
        death_year = int(years_match.group(2))

    # Extract name by removing everything in parentheses and cleaning up
    name = re.sub(r'\([^)]*\)', '', main_creator).strip()

    return Artist(name=name, birth_year=birth_year, death_year=death_year)


def parse_images(raw_val: Any, row: pd.Series) -> list[Image]:
    """
    Cleveland has 3 columns: image_web, image_print, image_full
    Each image column will use the 'share_license_status' for copyright.
    """
    if pd.isna(raw_val):
        return []

    image_url = str(raw_val)
    # Fetch 'share_license_status' from the row
    share_license_status = row.get('share_license_status', None)
    if pd.isna(share_license_status):
        share_license_status = None
    else:
        share_license_status = str(share_license_status)

    return [Image(url=image_url, copyright=share_license_status)]


class ClevelandMuseumDataProcessor(BaseMuseumDataProcessor):
    # Our base class will call load_data, so define it
    def load_data(self, file_path: str, dev_mode: bool = False) -> pd.DataFrame:
        nrows = self.DEV_MODE_ROWS if dev_mode else None
        return pd.read_csv(file_path, encoding='utf-8', low_memory=False, nrows=nrows)

    def get_museum_name(self) -> str:
        return "Cleveland Museum of Art"

    # Here's where we define the column mapping
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
    data = processor.get_unified_data("../../data/source_datasets/cleveland_museum_of_art.csv")
    print(f"Processed {len(data)} artworks.")
    for artwork in data[:3]:
        print(artwork.dict())