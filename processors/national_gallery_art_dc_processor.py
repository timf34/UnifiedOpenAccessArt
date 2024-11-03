import pandas as pd
import re
from typing import List, Optional
from datetime import datetime

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation, Provenance


class NGADataProcessor(BaseMuseumDataProcessor):
    def load_data(self, file_path: str) -> pd.DataFrame:
        df = pd.read_csv(file_path, encoding='utf-8', nrows=100)  # Temp limiting to 100 rows for testing
        return df.dropna(how='all')  # Remove completely empty rows

    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
        unified_data = []
        for _, row in df.iterrows():
            try:
                artwork = self._create_artwork(row)
                if artwork:  # Only add if we successfully created an artwork
                    unified_data.append(artwork)
            except Exception as e:
                print(f"Error processing row with title '{row.get('title', 'Unknown')}': {str(e)}")
                continue

        return unified_data

    def _create_artwork(self, row: pd.Series) -> Optional[UnifiedArtwork]:
        """Create a UnifiedArtwork object from a row of data."""
        if pd.isna(row['title']) and pd.isna(row['accessionnum']):
            return None  # Skip rows without basic identifying information

        artist = Artist(
            name=row['attributioninverted'] if pd.notna(row['attributioninverted']) else row['attribution'],
            birth_date=None,  # Would need additional parsing of attribution text
            death_date=None,
            nationality=None,  # Not directly provided in the data
            biography=None,
            role=None
        )

        dimensions = self._parse_dimensions(row['dimensions'] if pd.notna(row['dimensions']) else "")

        location = ArtworkLocation(
            gallery=None,
            room=None,
            wall=None,
            current_location=row['locationid'] if pd.notna(row['locationid']) else None
        )

        images = []
        if pd.notna(row['customprinturl']):
            images.append(Image(
                url=row['customprinturl'],
                copyright=None,
                type="print"
            ))

        return UnifiedArtwork(
            id=str(row['objectid']),
            accession_number=row['accessionnum'],
            title=row['title'],
            artist=artist,
            date_created=row['displaydate'] if pd.notna(row['displaydate']) else None,
            date_start=row['beginyear'] if pd.notna(row['beginyear']) else None,
            date_end=row['endyear'] if pd.notna(row['endyear']) else None,
            medium=row['medium'] if pd.notna(row['medium']) else None,
            dimensions=dimensions,
            credit_line=row['creditline'] if pd.notna(row['creditline']) else None,
            department=row['departmentabbr'] if pd.notna(row['departmentabbr']) else None,
            classification=row['classification'] if pd.notna(row['classification']) else None,
            object_type=row['subclassification'] if pd.notna(row['subclassification']) else None,
            culture=None,
            period=None,
            dynasty=None,
            provenance=self._parse_provenance(row['provenancetext'] if pd.notna(row['provenancetext']) else ""),
            description=None,
            exhibition_history=None,
            bibliography=None,
            images=images,
            is_public_domain=True,  # NGA's open access policy
            rights_and_reproduction=None,
            location=location,
            url=None,  # Would need to construct from base URL + objectid
            source_museum="National Gallery of Art DC",
            original_metadata=row.to_dict()
        )

    def _parse_dimensions(self, dimensions_str: str) -> List[Dimension]:
        """Parse NGA's complex dimension string format."""
        dimensions = []
        if not dimensions_str:
            return dimensions

        # Split multiple dimension entries
        for entry in dimensions_str.split(';'):
            entry = entry.strip()
            if not entry:
                continue

            # Try to find dimension values with units
            matches = re.findall(r'(\d+\.?\d*)\s*[×x]\s*(\d+\.?\d*)\s*(?:×\s*(\d+\.?\d*))?\s*(cm|in)', entry)
            if matches:
                for match in matches:
                    values = [float(x) for x in match[:-1] if x]  # Convert all numbers to float
                    unit = match[-1]

                    # Assign dimensions in order: width, height, depth
                    dimension_types = ['width', 'height', 'depth']
                    for value, dim_type in zip(values, dimension_types):
                        dimensions.append(Dimension(
                            value=value,
                            unit=unit,
                            type=dim_type
                        ))

        return dimensions

    def _parse_provenance(self, provenance_text: str) -> List[Provenance]:
        """Parse NGA's detailed provenance text."""
        if not provenance_text:
            return []

        provenance_entries = []
        # Split on semicolons or periods for separate entries
        entries = re.split(r'[;.]', provenance_text)

        for entry in entries:
            entry = entry.strip()
            if entry:
                provenance_entries.append(Provenance(
                    description=entry,
                    date=None  # We could parse dates but would need more sophisticated date extraction
                ))

        return provenance_entries


def main():
    processor = NGADataProcessor()
    unified_data = processor.get_unified_data('../data/source_datasets/national_gallery_of_art_dc.csv')

    # Print first 10 records
    for artwork in unified_data[:10]:
        print(artwork)
        print()

    print(f"Total processed: {len(unified_data)}")


if __name__ == '__main__':
    main()
