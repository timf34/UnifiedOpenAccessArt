import re
import pandas as pd
from typing import List
from datetime import datetime

from base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation, Provenance


class ClevelandMuseumDataProcessor(BaseMuseumDataProcessor):
    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path, encoding='utf-8', nrows=100)  # Temp limiting to 100 rows for testing

    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
        unified_data = []
        for _, row in df.iterrows():
            artist = self.parse_artist(row['creators'])

            dimensions = self.parse_dimensions(row['measurements'])

            images = self.parse_images(row)

            location = ArtworkLocation(
                gallery=None,
                room=None,
                wall=None,
                current_location=row['current_location'] if pd.notna(row['current_location']) else None
            )

            artwork = UnifiedArtwork(
                id=str(row['id']),
                accession_number=row['accession_number'],
                title=row['title'],
                artist=artist,
                date_created=row['creation_date'] if pd.notna(row['creation_date']) else None,
                date_start=self.parse_year(row['creation_date_earliest']),
                date_end=self.parse_year(row['creation_date_latest']),
                medium=row['technique'] if pd.notna(row['technique']) else None,
                dimensions=dimensions,
                credit_line=row['creditline'] if pd.notna(row['creditline']) else None,
                department=row['department'] if pd.notna(row['department']) else None,
                classification=row['type'] if pd.notna(row['type']) else None,
                object_type=row['type'] if pd.notna(row['type']) else None,
                culture=row['culture'] if pd.notna(row['culture']) else None,
                period=None,
                dynasty=None,
                provenance=self.parse_provenance(row['provenance']),
                description=row['description'] if pd.notna(row['description']) else None,
                exhibition_history=row['exhibitions'] if pd.notna(row['exhibitions']) else None,
                bibliography=row['citations'] if pd.notna(row['citations']) else None,
                images=images,
                is_public_domain=row['share_license_status'] == 'CC0',
                rights_and_reproduction=row['copyright'] if pd.notna(row['copyright']) else None,
                location=location,
                url=row['url'] if pd.notna(row['url']) else None,
                source_museum="Cleveland Museum of Art",
                original_metadata=row.to_dict()
            )
            unified_data.append(artwork)

        return unified_data

    def parse_dimensions(self, dimensions_str: str) -> List[Dimension]:
        if pd.isna(dimensions_str):
            return []

        dimensions = []
        parts = dimensions_str.split(';')
        for part in parts:
            if ':' in part:
                dim_type, value = part.split(':')
                value = value.strip()
                if 'x' in value:
                    values = value.split('x')
                    for i, v in enumerate(values):
                        dim_type = ['width', 'height', 'depth'][i] if i < 3 else 'unknown'
                        v = v.strip()
                        if v:
                            value, unit = self.extract_value_and_unit(v)
                            dimensions.append(Dimension(value=value, unit=unit, type=dim_type))
                else:
                    value, unit = self.extract_value_and_unit(value)
                    dimensions.append(Dimension(value=value, unit=unit, type=dim_type.strip().lower()))
        return dimensions

    def extract_value_and_unit(self, value_str: str):
        parts = value_str.split()
        value = float(parts[0])
        unit = ' '.join(parts[1:]) if len(parts) > 1 else 'cm'
        return value, unit

    def parse_year(self, date_str):
        if pd.isna(date_str):
            return None
        try:
            return int(date_str)
        except ValueError:
            return None

    def parse_provenance(self, provenance_text):
        if pd.isna(provenance_text):
            return []

        provenance_entries = []
        for entry in provenance_text.split(';'):
            entry = entry.strip()
            date = None
            description = entry

            # Try to extract a date from the entry
            date_match = re.search(r'\d{4}', entry)
            if date_match:
                date = date_match.group()
                description = entry.replace(date, '').strip()

            provenance_entries.append(Provenance(
                text=entry,
                description=description,
                date=date
            ))

        return provenance_entries

    def parse_artist(self, artists_str):
        if pd.isna(artists_str):
            return None
        artist_info = artists_str.split(';')[0]  # Take the first artist if multiple are listed
        name, role = artist_info.rsplit(',', 1) if ',' in artist_info else (artist_info, "")
        return Artist(
            name=name.strip(),
            birth_date=None,
            death_date=None,
            nationality=None,
            biography=None,
            role=role.strip()
        )

    def parse_images(self, row):
        images = []
        if pd.notna(row['image_web']):
            images.append(Image(
                url=row['image_web'],
                copyright=None,
                type="primary"
            ))
        if pd.notna(row['image_print']):
            images.append(Image(
                url=row['image_print'],
                copyright=None,
                type="print"
            ))
        return images


# Usage
processor = ClevelandMuseumDataProcessor()
unified_data = processor.get_unified_data('../data/source_datasets/cleveland_museum_of_art.csv')

