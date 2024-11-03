"""Carnegie Museum of Art"""
import pandas as pd
import re
from typing import List, Optional
from datetime import datetime

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation


class CMOADataProcessor(BaseMuseumDataProcessor):
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
                print(f"Error processing row with title '{row.get('title', 'Unknown')}': {str(e)}")
                continue
        return unified_data

    def _create_artwork(self, row: pd.Series) -> Optional[UnifiedArtwork]:
        """Create a UnifiedArtwork object from a row of CMOA data."""
        if pd.isna(row['title']):
            return None

        artist = self._parse_artist_info(row)
        dimensions = self._parse_dimensions(row)
        start_date, end_date = self._parse_dates(row)

        location = ArtworkLocation(
            gallery=None,
            room=None,
            wall=None,
            current_location=row['physical_location'] if pd.notna(row['physical_location']) else None
        )

        images = []
        if pd.notna(row['image_url']):
            images.append(Image(
                url=row['image_url'],
                copyright=None,
                type="primary"
            ))

        if pd.notna(row['web_url']):
            images.append(Image(
                url=row['web_url'],
                copyright=None,
                type="web"
            ))

        return UnifiedArtwork(
            id=str(row['id']),
            accession_number=str(row['accession_number']),
            title=row['title'],
            artist=artist,
            date_created=row['creation_date'] if pd.notna(row['creation_date']) else None,
            date_start=start_date,
            date_end=end_date,
            medium=row['medium'] if pd.notna(row['medium']) else None,
            dimensions=dimensions,
            credit_line=row['credit_line'] if pd.notna(row['credit_line']) else None,
            department=row['department'] if pd.notna(row['department']) else None,
            classification=row['classification'] if pd.notna(row['classification']) else None,
            object_type=None,  # Not directly provided in the data
            culture=None,  # Not provided in the data
            period=None,
            dynasty=None,
            provenance=[],  # Could parse provenance_text if needed
            description=None,
            exhibition_history=None,
            bibliography=None,
            images=images,
            is_public_domain=True,  # Assuming open access
            rights_and_reproduction=None,
            location=location,
            url=row['web_url'] if pd.notna(row['web_url']) else None,
            source_museum="Carnegie Museum of Art",
            original_metadata=row.to_dict()
        )

    def _parse_artist_info(self, row: pd.Series) -> Artist:
        """Parse artist information from multiple fields."""
        name = None
        if pd.notna(row['cited_name']):
            name = row['cited_name']
        elif pd.notna(row['full_name']):
            name = row['full_name']

        if not name:
            return Artist(
                name="Unknown",
                birth_date=None,
                death_date=None,
                nationality=None,
                biography=None,
                role=None
            )

        # Parse birth and death dates
        birth_date = None
        death_date = None

        if pd.notna(row['birth_date']):
            try:
                birth_date = str(pd.to_datetime(row['birth_date']).year)
            except Exception:
                pass

        if pd.notna(row['death_date']):
            try:
                death_date = str(pd.to_datetime(row['death_date']).year)
            except Exception:
                pass

        return Artist(
            name=name,
            birth_date=birth_date,
            death_date=death_date,
            nationality=row['nationality'] if pd.notna(row['nationality']) else None,
            biography=None,
            role=row['role'] if pd.notna(row['role']) else None
        )

    def _parse_dates(self, row: pd.Series) -> tuple[Optional[int], Optional[int]]:
        """Parse start and end dates from various date fields."""
        start_date = None
        end_date = None

        # Try to parse earliest and latest dates first
        if pd.notna(row['creation_date_earliest']):
            try:
                start_date = pd.to_datetime(row['creation_date_earliest']).year
            except Exception:
                pass

        if pd.notna(row['creation_date_latest']):
            try:
                end_date = pd.to_datetime(row['creation_date_latest']).year
            except Exception:
                pass

        # If those fail, try to parse from creation_date
        if pd.notna(row['creation_date']) and not (start_date and end_date):
            date_str = str(row['creation_date'])

            # Handle range format like "1964-1965"
            if '-' in date_str:
                parts = date_str.split('-')
                try:
                    start_date = int(parts[0])
                    end_date = int(parts[1])
                except (ValueError, IndexError):
                    pass
            # Handle single year
            else:
                try:
                    year = int(date_str)
                    start_date = year
                    end_date = year
                except ValueError:
                    pass

        return start_date, end_date

    def _parse_dimensions(self, row: pd.Series) -> List[Dimension]:
        """Parse dimensions from individual dimension fields."""
        dimensions = []
        dimension_fields = {
            'item_width': 'width',
            'item_height': 'height',
            'item_depth': 'depth',
            'item_diameter': 'diameter'
        }

        for field, dim_type in dimension_fields.items():
            if pd.notna(row[field]) and float(row[field]) > 0:
                dimensions.append(Dimension(
                    value=float(row[field]),
                    unit='inches',  # CMOA typically uses inches
                    type=dim_type
                ))

        return dimensions


def main():
    processor = CMOADataProcessor()
    unified_data = processor.get_unified_data('../data/source_datasets/cmoa.csv')

    # Print first 10 records
    for artwork in unified_data[:10]:
        print(artwork)
        print()

    print(f"Total processed: {len(unified_data)}")


if __name__ == '__main__':
    main()
