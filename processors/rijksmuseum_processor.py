import pandas as pd
import re
from typing import List, Optional, Tuple
from datetime import datetime

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation


class RMADataProcessor(BaseMuseumDataProcessor):
    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path, encoding='utf-8', nrows=100)  # Temp limiting to 100 rows for testing

    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
        unified_data = []
        for _, row in df.iterrows():
            try:
                artwork = self._create_artwork(row)
                if artwork:
                    unified_data.append(artwork)
            except Exception as e:
                print(f"Error processing row with ID '{row.get('objectInventoryNumber', 'Unknown')}': {str(e)}")
                continue
        return unified_data

    def _create_artwork(self, row: pd.Series) -> Optional[UnifiedArtwork]:
        """Create a UnifiedArtwork object from a row of Rijksmuseum data."""
        if pd.isna(row['objectInventoryNumber']):
            return None

        # Parse artist information
        artist = self._parse_artist_info(row)

        # Parse dates
        date_start, date_end = self._parse_dates(row)

        # Create images list
        images = self._parse_images(row)

        # Create location object
        location = ArtworkLocation(
            gallery="Rijksmuseum",
            room=None,
            wall=None,
            current_location=None
        )

        # Handle date_created - convert to string if it's a float
        date_created = None
        if pd.notna(row['objectCreationDate[1]']):
            if isinstance(row['objectCreationDate[1]'], float):
                date_created = str(int(row['objectCreationDate[1]']))
            else:
                date_created = str(row['objectCreationDate[1]'])

        return UnifiedArtwork(
            id=str(row['objectInventoryNumber']),
            accession_number=str(row['objectInventoryNumber']),
            title=row['objectTitle[1]'] if pd.notna(row['objectTitle[1]']) else 'Untitled',
            artist=artist,
            date_created=date_created,
            date_start=date_start,
            date_end=date_end,
            medium=None,  # Not provided in sample data
            dimensions=[],  # Not provided in sample data
            credit_line=None,  # Not provided in sample data
            department=None,  # Not provided in sample data
            classification=row['objectType[1]'] if pd.notna(row['objectType[1]']) else None,
            object_type=row['objectType[1]'] if pd.notna(row['objectType[1]']) else None,
            culture=None,  # Not provided in sample data
            period=None,  # Not provided in sample data
            dynasty=None,
            provenance=[],  # Not provided in sample data
            description=None,  # Not provided in sample data
            exhibition_history=None,
            bibliography=None,
            images=images,
            is_public_domain=True,  # Assuming open access based on image availability
            rights_and_reproduction=None,
            location=location,
            url=row['objectPersistentIdentifier'] if pd.notna(row['objectPersistentIdentifier']) else None,
            source_museum="Rijksmuseum",
            original_metadata=row.to_dict()
        )

    def _parse_artist_info(self, row: pd.Series) -> Artist:
        """Parse artist information from the creator field."""
        creator = row.get('objectCreator[1]', '')

        if pd.isna(creator) or creator.lower() == 'anonymous':
            name = "Unknown"
        else:
            name = creator

        return Artist(
            name=name,
            birth_date=None,  # Not provided in data
            death_date=None,  # Not provided in data
            nationality=None,  # Not provided in data
            biography=None,
            role=None
        )

    def _parse_dates(self, row: pd.Series) -> Tuple[Optional[int], Optional[int]]:
        """Parse date information from creation date field."""
        date_str = row.get('objectCreationDate[1]', '')

        if pd.isna(date_str):
            return None, None

        # If it's a float, convert it to an integer
        if isinstance(date_str, float):
            year = int(date_str)
            return year, year

        date_str = str(date_str)

        # Handle single year
        if date_str.isdigit():
            year = int(date_str)
            return year, year

        # Try to extract year from various formats
        year_match = re.search(r'\b(\d{4})\b', date_str)
        if year_match:
            year = int(year_match.group(1))
            return year, year

        return None, None

    def _parse_images(self, row: pd.Series) -> List[Image]:
        """Parse image information."""
        images = []

        if pd.notna(row['objectImage']):
            images.append(Image(
                url=row['objectImage'],
                copyright=None,
                type="primary"
            ))

        return images


def main():
    processor = RMADataProcessor()
    unified_data = processor.get_unified_data('../data/source_datasets/202001-rma-csv-collection.csv')

    # Print first 10 records
    for artwork in unified_data[:10]:
        print(artwork)
        print()

    print(f"Total processed: {len(unified_data)}")


if __name__ == '__main__':
    main()
