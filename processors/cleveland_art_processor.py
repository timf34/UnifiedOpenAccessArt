import re
import pandas as pd
from typing import List, Optional
from datetime import datetime

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation, Provenance


class ClevelandMuseumDataProcessor(BaseMuseumDataProcessor):
    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path, encoding='utf-8', nrows=100)  # Temp limiting to 100 rows for testing

    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
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
        """Create a UnifiedArtwork object from a row of data."""
        return UnifiedArtwork(
            id=str(row.get('id', '')),
            accession_number=str(row.get('accession_number', '')),
            title=str(row.get('title', 'Untitled')),  # Fallback to 'Untitled' if missing
            artist=self._parse_artist(row),
            date_created=row.get('creation_date'),
            date_start=self._parse_year(row.get('creation_date_earliest')),
            date_end=self._parse_year(row.get('creation_date_latest')),
            medium=row.get('medium'),
            dimensions=self._parse_dimensions(row),
            credit_line=row.get('credit_line'),
            department=row.get('department'),
            classification=row.get('classification'),
            object_type=row.get('classification'),  # Using classification as object_type
            culture=row.get('culture'),  # Optional
            period=row.get('period'),  # Optional
            dynasty=row.get('dynasty'),  # Optional
            provenance=self._parse_provenance(row.get('provenance_text', '')),
            description=row.get('description'),
            exhibition_history=row.get('exhibition_history'),
            bibliography=row.get('bibliography'),
            images=self._parse_images(row),
            is_public_domain=bool(row.get('is_public_domain', False)),  # Defaults to False
            rights_and_reproduction=row.get('rights_and_reproduction'),
            location=self._parse_location(row),
            url=row.get('web_url'),
            source_museum="Cleveland Museum of Art",
            original_metadata=row.to_dict()
        )

    def _parse_dimensions(self, row: pd.Series) -> List[Dimension]:
        """Parse dimensions from individual dimension fields."""
        dimensions = []
        dimension_mapping = {
            'item_width': 'width',
            'item_height': 'height',
            'item_depth': 'depth',
            'item_diameter': 'diameter'
        }

        for field, dim_type in dimension_mapping.items():
            value = row.get(field)
            if pd.notna(value) and float(value) > 0:
                dimensions.append(Dimension(
                    value=float(value),
                    unit='inches',  # Based on sample data
                    type=dim_type
                ))

        return dimensions

    def _parse_year(self, date_str: Optional[str]) -> Optional[int]:
        """Parse year from date string."""
        if pd.isna(date_str):
            return None
        try:
            # Handle dates in format MM/DD/YYYY
            parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
            return parsed_date.year
        except (ValueError, TypeError):
            return None

    def _parse_provenance(self, provenance_text: str) -> List[Provenance]:
        """Parse provenance text into structured format."""
        if pd.isna(provenance_text) or not provenance_text.strip():
            return []

        provenance_entries = []
        entries = provenance_text.split(';')

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            # Simple date extraction - looking for years
            date_match = re.search(r'\b\d{4}\b', entry)

            provenance_entries.append(Provenance(
                description=entry,
                # Don't try to parse the date string, just store the description
                date=None
            ))

        return provenance_entries

    def _parse_artist(self, row: pd.Series) -> Artist:
        """Parse artist information from the 'creators' column."""
        creators = row.get('creators', '')
        if not creators or pd.isna(creators):
            return Artist(
                name='Unknown',
                birth_date=None,
                death_date=None,
                nationality=None,
                biography=None,
                role=None
            )

        # Split by parentheses to extract the main parts
        try:
            name_part, details_part = creators.split('(', 1)
            name = name_part.strip().lower()

            # Further split the details part to extract nationality, dates, and role
            details_part = details_part.strip(')')
            details = details_part.split(',')
            nationality = details[0].strip() if len(details) > 0 else None

            # Extract birth and death years
            date_part = details[1].strip() if len(details) > 1 else None
            birth_year, death_year = None, None
            if date_part and '-' in date_part:
                birth_year, death_year = date_part.split('-')
                birth_year = int(birth_year.strip()) if birth_year.strip().isdigit() else None
                death_year = int(death_year.strip()) if death_year.strip().isdigit() else None

            # Extract role (e.g., "artist", "sculptor") if it exists
            role = details[2].strip() if len(details) > 2 else None

            return Artist(
                name=name,
                birth_date=birth_year,
                death_date=death_year,
                nationality=nationality,
                biography=None,
                role=role
            )

        except ValueError:
            # In case of unexpected format, return a fallback
            return Artist(
                name=creators.lower(),
                birth_date=None,
                death_date=None,
                nationality=None,
                biography=None,
                role=None
            )

    def _parse_images(self, row: pd.Series) -> List[Image]:
        """Parse image information."""
        images = []
        if pd.notna(row.get('image_url')):
            images.append(Image(
                url=row['image_url'],
                copyright=None,
                type="primary"
            ))
        return images

    def _parse_location(self, row: pd.Series) -> ArtworkLocation:
        """Parse location information."""
        return ArtworkLocation(
            gallery=None,
            room=None,
            wall=None,
            current_location=row.get('physical_location')
        )


# Usage example
if __name__ == "__main__":
    processor = ClevelandMuseumDataProcessor()
    unified_data = processor.get_unified_data('../data/source_datasets/cleveland_museum_of_art.csv')
    print(f"Processed {len(unified_data)} artworks")

    for artwork in unified_data[:10]:
        print(artwork)
        print("\n\n")
