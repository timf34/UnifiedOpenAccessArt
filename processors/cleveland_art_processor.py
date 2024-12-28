import re
import pandas as pd
from typing import List, Optional
from datetime import datetime

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Museum, ArtObject, Image, DateInfo, DateType


class ClevelandMuseumDataProcessor(BaseMuseumDataProcessor):
    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        Load CSV data using pandas.
        """
        return pd.read_csv(file_path, encoding='utf-8', low_memory=False)

    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
        """
        Process each row in the DataFrame to create UnifiedArtwork objects.
        """
        unified_data = []
        for _, row in df.iterrows():
            try:
                artwork = self._create_artwork(row)
                unified_data.append(artwork)
            except Exception as e:
                print(f"Error processing row {row.get('id', 'unknown')}: {str(e)}")
                continue
        return unified_data

    def _create_artwork(self, row: pd.Series) -> UnifiedArtwork:
        """
        Create a UnifiedArtwork object from a row of data.
        """
        return UnifiedArtwork(
            id=f"cleveland_{str(row.get('id', ''))}",
            museum=Museum(name="Cleveland Museum of Art"),
            object=ArtObject(
                name=str(row.get('title', 'Untitled')),
                creation_date=self._parse_date(row),
                type=row.get('type')  # Correctly mapping 'type' field
            ),
            artist=self._parse_artist(row),
            images=self._parse_images(row),
            web_url=row.get('url'),  # Assuming 'url' is the correct web URL field
            metadata=self._create_metadata(row)
        )

    def _parse_date(self, row: pd.Series) -> Optional[DateInfo]:
        """
        Parse creation date into standardized format.
        """
        # Extract earliest and latest dates
        earliest = row.get('creation_date_earliest')
        latest = row.get('creation_date_latest')
        display_text = row.get('creation_date', '')

        if pd.isna(display_text):
            return None

        # Try to parse earliest and latest
        start_year = self._parse_year(earliest)
        end_year = self._parse_year(latest)

        # Determine date type
        if start_year is None and end_year is None:
            # Attempt to parse display_text as a single year
            start_year = self._parse_year(display_text)
            if start_year:
                return DateInfo(
                    type=DateType.YEAR,
                    display_text=str(display_text),
                    start_year=start_year,
                    end_year=start_year
                )
            else:
                return DateInfo(
                    type=DateType.UNKNOWN,
                    display_text=str(display_text),
                    start_year=None,
                    end_year=None
                )
        elif start_year is not None and end_year is None:
            return DateInfo(
                type=DateType.YEAR,
                display_text=str(display_text),
                start_year=start_year,
                end_year=start_year
            )
        elif start_year == end_year:
            return DateInfo(
                type=DateType.YEAR,
                display_text=str(display_text),
                start_year=start_year,
                end_year=start_year
            )
        elif start_year is not None and end_year is not None:
            return DateInfo(
                type=DateType.YEAR_RANGE,
                display_text=str(display_text),
                start_year=start_year,
                end_year=end_year
            )
        else:
            return DateInfo(
                type=DateType.UNKNOWN,
                display_text=str(display_text),
                start_year=None,
                end_year=None
            )

    def _parse_year(self, date_str: Optional[str]) -> Optional[int]:
        """
        Parse year from date string.
        """
        if pd.isna(date_str):
            return None
        try:
            # Handle dates in format MM/DD/YYYY or YYYY
            if isinstance(date_str, str):
                # Extract the first four-digit number as the year
                match = re.search(r'(\d{4})', date_str)
                if match:
                    return int(match.group(1))
            elif isinstance(date_str, (int, float)):
                return int(date_str)
            return None
        except (ValueError, TypeError):
            return None

    def _parse_artist(self, row: pd.Series) -> Artist:
        """
        Parse artist information from the 'creators' field.
        """
        creators = row.get('creators', '')
        if not creators or pd.isna(creators):
            return Artist(
                name='Unknown Artist',
                birth_year=None,
                death_year=None
            )

        try:
            # Simplistic parsing: assume the first creator is the main artist
            # Split by semicolon or comma if multiple creators exist
            creators_list = re.split(r';|,', str(creators))
            main_creator = creators_list[0].strip()

            # Optionally, remove any non-alphabetic characters or unwanted tokens
            main_creator = re.sub(r'\([^)]*\)', '', main_creator).strip()

            return Artist(
                name=main_creator if main_creator else 'Unknown Artist',
                birth_year=None,  # Birth and death years are not provided in 'creators'
                death_year=None
            )
        except Exception:
            return Artist(
                name='Unknown Artist',
                birth_year=None,
                death_year=None
            )

    def _parse_images(self, row: pd.Series) -> List[Image]:
        """
        Parse image information from 'image_web', 'image_print', and 'image_full' fields.
        """
        images = []
        # List of image fields to check
        image_fields = ['image_web', 'image_print', 'image_full']
        for field in image_fields:
            url = row.get(field)
            if pd.notna(url):
                images.append(Image(
                    url=url,
                    copyright=None
                ))
        return images

    def _create_metadata(self, row: pd.Series) -> dict:
        """
        Store all additional metadata in a dictionary.
        Exclude fields already processed.
        """
        # Convert the row to a dictionary
        metadata = row.to_dict()
        # Fields already processed and should be excluded from metadata
        processed_fields = {
            'id', 'title', 'creators', 'creation_date',
            'creation_date_earliest', 'creation_date_latest',
            'type', 'image_web', 'image_print', 'image_full', 'url'
        }

        # Exclude processed fields and any NaN values
        return {
            k: v for k, v in metadata.items()
            if k not in processed_fields and pd.notna(v)
        }


if __name__ == "__main__":
    processor = ClevelandMuseumDataProcessor()
    unified_data = processor.get_unified_data('../data/source_datasets/cleveland_museum_of_art.csv')
    print(f"Processed {len(unified_data)} artworks\n")

    for artwork in unified_data[:5]:
        print(artwork.dict())
        print()
