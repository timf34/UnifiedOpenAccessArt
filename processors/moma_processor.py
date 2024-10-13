import pandas as pd
import re
from typing import List

from base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation


class MOMADataProcessor(BaseMuseumDataProcessor):
    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path, encoding='utf-8', nrows=100)  # TODO: Temp limiting to 100 rows for testing

    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
        unified_data = []
        for _, row in df.iterrows():
            # Function to clean and convert date strings
            def clean_date(date_str):
                if pd.isna(date_str):
                    return None
                # Remove parentheses and any non-digit characters
                cleaned = re.sub(r'\D', '', str(date_str))
                return int(cleaned) if cleaned else None
            #
            # print(row)
            # print("\n\n ---------------- \n\n")
            begin_date = clean_date(row['BeginDate'])
            end_date = clean_date(row['EndDate'])

            artist = Artist(
                name=row['Artist'],
                birth_date=str(abs(begin_date)) if begin_date and begin_date < 0 else None,
                death_date=str(end_date) if end_date and end_date > 0 else None,
                nationality=row['Nationality'].strip('()'),
                biography=row['ArtistBio'],
                role="artist"
            )

            dimensions = self.parse_dimensions(row)

            # Handle potentially empty or NaN ImageURL
            images = []
            if pd.notna(row['ImageURL']):
                images.append(Image(
                    url=row['ImageURL'],
                    copyright=None,  # MOMA data doesn't provide this information
                    type="primary"
                ))

            location = ArtworkLocation(
                gallery=None,  # MOMA data doesn't provide this information
                room=None,
                wall=None,
                current_location="On View" if row['OnView'] == 'Y' else "Not on View"
            )

            artwork = UnifiedArtwork(
                id=str(row['ObjectID']),
                accession_number=row['AccessionNumber'],
                title=row['Title'],
                artist=artist,
                date_created=row['Date'],
                date_start=None,  # Would need more complex parsing of 'Date' field
                date_end=None,
                medium=row['Medium'] if pd.notna(row['Medium']) else None,
                dimensions=dimensions,
                credit_line=row['CreditLine'],
                department=row['Department'],
                classification=row['Classification'],
                object_type=None,  # MOMA data doesn't provide this information
                culture=None,
                period=None,
                dynasty=None,
                provenance=[],  # MOMA data doesn't provide this information
                description=None,
                exhibition_history=None,
                bibliography=None,
                images=images,
                is_public_domain=False,  # MOMA data doesn't provide this information
                rights_and_reproduction=None,
                location=location,
                url=row['URL'] if pd.notna(row['URL']) else None,
                source_museum="MOMA",
                original_metadata=row.to_dict()
            )
            unified_data.append(artwork)

        return unified_data

    def parse_dimensions(self, row) -> List[Dimension]:
        dimensions = []
        dimension_fields = ['Height (cm)', 'Width (cm)', 'Depth (cm)', 'Diameter (cm)', 'Weight (kg)']

        for field in dimension_fields:
            if pd.notna(row[field]):
                dim_type = field.split()[0].lower()
                dimensions.append(Dimension(
                    value=float(row[field]),
                    unit="cm" if "cm" in field else "kg",
                    type=dim_type
                ))

        return dimensions


# Usage
processor = MOMADataProcessor()
unified_data = processor.get_unified_data('../data/source_datasets/moma.csv')

