import pandas as pd
import re
from typing import List, Optional, Tuple
from datetime import datetime

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation


class PennMuseumDataProcessor(BaseMuseumDataProcessor):
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
                print(f"Error processing row with ID '{row.get('identifier', 'Unknown')}': {str(e)}")
                continue
        return unified_data

    def _create_artwork(self, row: pd.Series) -> Optional[UnifiedArtwork]:
        """Create a UnifiedArtwork object from a row of Penn Museum data."""
        if pd.isna(row['identifier']):
            return None

        # Use title field if available, otherwise objectName
        title = row['title'] if pd.notna(row['title']) else row['objectName']

        # Handle creator information
        artist = self._parse_artist_info(row)

        # Parse dates
        date_start, date_end = self._parse_dates(row)

        # Parse dimensions
        dimensions = self._parse_dimensions(row)

        # Parse location
        location = self._parse_location(row)

        # Combine materials and technique for medium
        medium = self._combine_medium_info(row)

        return UnifiedArtwork(
            id=str(row['emuIRN']),
            accession_number=str(row['identifier']),
            title=title,
            artist=artist,
            date_created=row['dateMade'] if pd.notna(row['dateMade']) else None,
            date_start=date_start,
            date_end=date_end,
            medium=medium,
            dimensions=dimensions,
            credit_line=row['creditLine'] if pd.notna(row['creditLine']) else None,
            department=row['curatorialSection'] if pd.notna(row['curatorialSection']) else None,
            classification=row['objectName'] if pd.notna(row['objectName']) else None,
            object_type=None,
            culture=self._parse_culture(row),
            period=row['period'] if pd.notna(row['period']) else None,
            dynasty=None,
            provenance=[],  # Could parse from description if needed
            description=row['description'] if pd.notna(row['description']) else None,
            exhibition_history=None,
            bibliography=None,
            images=[],  # No image URLs in the sample data
            is_public_domain=True,  # Assuming open access
            rights_and_reproduction=None,
            location=location,
            url=None,
            source_museum="Penn Museum",
            original_metadata=row.to_dict()
        )

    def _parse_artist_info(self, row: pd.Series) -> Artist:
        """Parse artist information."""
        return Artist(
            name=row['creator'] if pd.notna(row['creator']) else "Unknown",
            birth_date=None,
            death_date=None,
            nationality=None,
            biography=None,
            role=None
        )

    def _parse_dates(self, row: pd.Series) -> Tuple[Optional[int], Optional[int]]:
        """Parse start and end dates."""
        start_date = None
        end_date = None

        # Try early/late dates first
        if pd.notna(row['earlyDate']):
            try:
                start_date = int(row['earlyDate'])
            except (ValueError, TypeError):
                pass

        if pd.notna(row['lateDate']):
            try:
                end_date = int(row['lateDate'])
            except (ValueError, TypeError):
                pass

        # If no early/late dates, try to parse dateMade
        if pd.notna(row['dateMade']) and not (start_date and end_date):
            # Handle decade format like "1960's"
            decade_match = re.match(r"(\d{3})0's", str(row['dateMade']))
            if decade_match:
                start_date = int(f"{decade_match.group(1)}0")
                end_date = int(f"{decade_match.group(1)}9")

        return start_date, end_date

    def _parse_dimensions(self, row: pd.Series) -> List[Dimension]:
        """Parse dimensions, handling dual unit system."""
        dimensions = []
        dimension_fields = {
            'depth': 'depth',
            'length': 'length',
            'width': 'width',
            'height': 'height',
            'thickness': 'thickness',
            'outsideDiameter': 'diameter'
        }

        # Default to centimeters if no unit specified
        unit = 'cm'
        if pd.notna(row['measurementUnit']):
            if 'inches' in row['measurementUnit'].lower():
                unit = 'in'

        for field, dim_type in dimension_fields.items():
            if pd.notna(row[field]) and float(row[field]) > 0:
                try:
                    dimensions.append(Dimension(
                        value=float(row[field]),
                        unit=unit,
                        type=dim_type
                    ))
                except (ValueError, TypeError):
                    continue

        return dimensions

    def _parse_location(self, row: pd.Series) -> ArtworkLocation:
        """Parse location information."""
        return ArtworkLocation(
            gallery=None,
            room=None,
            wall=None,
            current_location=row['locus'] if pd.notna(row['locus']) else None
        )

    def _combine_medium_info(self, row: pd.Series) -> Optional[str]:
        """Combine material and technique information."""
        medium_parts = []

        if pd.notna(row['material']):
            medium_parts.append(row['material'])

        if pd.notna(row['technique']):
            medium_parts.append(row['technique'])

        return "; ".join(medium_parts) if medium_parts else None

    def _parse_culture(self, row: pd.Series) -> Optional[str]:
        """Combine culture information."""
        culture_parts = []

        if pd.notna(row['culture']):
            culture_parts.append(row['culture'])

        if pd.notna(row['cultureArea']):
            culture_parts.append(row['cultureArea'])

        return " - ".join(culture_parts) if culture_parts else None


def main():
    processor = PennMuseumDataProcessor()
    unified_data = processor.get_unified_data('../data/source_datasets/Penn_Museum_Collections_Data.csv')

    # Print first 10 records
    for artwork in unified_data[:10]:
        print(artwork)
        print()

    print(f"Total processed: {len(unified_data)}")


if __name__ == '__main__':
    main()
