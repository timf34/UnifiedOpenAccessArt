import pandas as pd
import re
from typing import List, Optional, Tuple

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation


class QAGOMADataProcessor(BaseMuseumDataProcessor):
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
                print(f"Error processing row with title '{row.get('Title', 'Unknown')}': {str(e)}")
                continue
        return unified_data

    def _parse_artist_info(self, artist_text: str) -> Artist:
        """Parse the complex artist string that includes name, nationality, birth/death dates."""
        if pd.isna(artist_text):
            return Artist(name="Unknown", birth_date=None, death_date=None, nationality=None,
                          biography=None, role=None)

        # Split into name and details parts
        parts = artist_text.strip().split('\n')
        if len(parts) < 2:
            return Artist(name=artist_text.strip(), birth_date=None, death_date=None,
                          nationality=None, biography=None, role=None)

        name = parts[0].strip()
        details = parts[1].strip()

        # Extract nationality and dates
        nationality = None
        birth_date = None
        death_date = None

        # Try to extract dates from format like "1868—1961"
        date_match = re.search(r'(\d{4})(?:[-â€"](\d{4}))?', details)
        if date_match:
            birth_date = date_match.group(1)
            death_date = date_match.group(2) if date_match.group(2) else None

        # Extract nationality - everything before the dates
        if date_match:
            nationality_part = details[:date_match.start()].strip()
            nationality = nationality_part.split()[-1] if nationality_part else None

        return Artist(
            name=name,
            birth_date=birth_date,
            death_date=death_date,
            nationality=nationality,
            biography=None,
            role=None
        )

    def _parse_date(self, date_str: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse various date formats to extract start and end years."""
        if pd.isna(date_str):
            return None, None

        date_str = str(date_str).strip().lower()

        # Handle single year: "1961"
        if date_str.isdigit():
            year = int(date_str)
            return year, year

        # Handle "c.1926-33" format
        match = re.search(r'c\.?(\d{4})-(\d{2})', date_str)
        if match:
            start_year = int(match.group(1))
            end_year = int(match.group(1)[:2] + match.group(2))
            return start_year, end_year

        # Handle "1745, repr. 19th C." format
        match = re.search(r'(\d{4})', date_str)
        if match:
            return int(match.group(1)), int(match.group(1))

        return None, None

    def _parse_dimensions(self, dim_str: str) -> List[Dimension]:
        """Parse dimension string like '20.2 x 14.4 cm' or '56 x 102.3 x 48.3cm'."""
        dimensions = []
        if pd.isna(dim_str):
            return dimensions

        # Remove spaces around x and before unit
        dim_str = re.sub(r'\s*x\s*', 'x', dim_str)
        dim_str = re.sub(r'\s*(cm|mm|m)\s*$', r'\1', dim_str)

        # Match dimensions
        parts = dim_str.split('x')
        dimension_types = ['height', 'width', 'depth']  # Standard order for QAGOMA

        if len(parts) > 0:
            unit_match = re.search(r'(cm|mm|m)$', parts[-1])
            unit = unit_match.group(1) if unit_match else 'cm'

            for i, part in enumerate(parts):
                if i >= len(dimension_types):
                    break

                value_match = re.search(r'(\d+\.?\d*)', part)
                if value_match:
                    try:
                        value = float(value_match.group(1))
                        dimensions.append(Dimension(
                            value=value,
                            unit=unit,
                            type=dimension_types[i]
                        ))
                    except ValueError:
                        continue

        return dimensions

    def _create_artwork(self, row: pd.Series) -> Optional[UnifiedArtwork]:
        """Create a UnifiedArtwork object from a row of QAGOMA data."""
        if pd.isna(row['Title']):
            return None

        artist = self._parse_artist_info(row['Person'])
        date_start, date_end = self._parse_date(row['DateCreated'])
        dimensions = self._parse_dimensions(row['PhysicalDimensions'])

        location = ArtworkLocation(
            gallery="Queensland Art Gallery",
            room=None,
            wall=None,
            current_location=None
        )

        images = []
        if pd.notna(row['CollectionOnlineAPI']):
            images.append(Image(
                url=row['CollectionOnlineAPI'],
                copyright=None,
                type="api"
            ))

        return UnifiedArtwork(
            id=str(row['irn']),
            accession_number=str(row['AccessionNo']),
            title=row['Title'],
            artist=artist,
            date_created=row['DateCreated'] if pd.notna(row['DateCreated']) else None,
            date_start=date_start,
            date_end=date_end,
            medium=row['PhyMediumText'] if pd.notna(row['PhyMediumText']) else None,
            dimensions=dimensions,
            credit_line=row['CreditLine'] if pd.notna(row['CreditLine']) else None,
            department=row['Department'] if pd.notna(row['Department']) else None,
            classification=row['PhysicalCategory'] if pd.notna(row['PhysicalCategory']) else None,
            object_type=row['ObjectType'] if pd.notna(row['ObjectType']) else None,
            culture=None,
            period=None,
            dynasty=None,
            provenance=[],  # No detailed provenance in the data
            description=None,
            exhibition_history=None,
            bibliography=None,
            images=images,
            is_public_domain=True,  # Assuming open access
            rights_and_reproduction=None,
            location=location,
            url=row['CollectionOnlineAPI'] if pd.notna(row['CollectionOnlineAPI']) else None,
            source_museum="Queensland Art Gallery",
            original_metadata=row.to_dict()
        )


def main():
    processor = QAGOMADataProcessor()
    unified_data = processor.get_unified_data('../data/source_datasets/qagoma-collection-artworks-september-2024.csv')

    # Print first 10 records
    for artwork in unified_data[:10]:
        print(artwork)
        print()

    print(f"Total processed: {len(unified_data)}")


if __name__ == '__main__':
    main()
