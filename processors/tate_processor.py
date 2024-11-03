import pandas as pd
import re
from typing import List
from datetime import datetime

from processors.base_processor import BaseMuseumDataProcessor
from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation


class TateDataProcessor(BaseMuseumDataProcessor):
    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path, encoding='utf-8', nrows=100)  # TODO: Temp limiting to 100 rows for testing

    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
        unified_data = []
        for _, row in df.iterrows():
            artist = Artist(
                name=row['artist'],
                birth_date=None,  # Tate data doesn't provide birth/death dates in this format
                death_date=None,
                nationality=None,  # Tate data doesn't provide nationality in this sample
                biography=None,
                role=row['artistRole']
            )

            dimensions = self.parse_dimensions(row)

            images = []
            if pd.notna(row['thumbnailUrl']):
                images.append(Image(
                    url=row['thumbnailUrl'],
                    copyright=row['thumbnailCopyright'] if pd.notna(row['thumbnailCopyright']) else None,
                    type="thumbnail"
                ))

            location = ArtworkLocation(
                gallery=None,
                room=None,
                wall=None,
                current_location=None  # Tate data doesn't provide current location in this sample
            )

            artwork = UnifiedArtwork(
                id=str(row['id']),
                accession_number=row['accession_number'],
                title=row['title'],
                artist=artist,
                date_created=row['dateText'],
                date_start=row['year'] if pd.notna(row['year']) else None,
                date_end=None,
                medium=row['medium'] if pd.notna(row['medium']) else "",
                dimensions=dimensions,
                credit_line=row['creditLine'] if pd.notna(row['creditLine']) else "",
                department=None,  # Tate data doesn't provide department in this sample
                classification=None,  # Tate data doesn't provide classification in this sample
                object_type=None,
                culture=None,
                period=None,
                dynasty=None,
                provenance=[],
                description=None,
                exhibition_history=None,
                bibliography=None,
                images=images,
                is_public_domain=False,  # Tate data doesn't provide this information in the sample
                rights_and_reproduction=None,
                location=location,
                url=row['url'] if pd.notna(row['url']) else "",
                source_museum="Tate",
                original_metadata=row.to_dict()
            )
            unified_data.append(artwork)

        return unified_data

    def parse_dimensions(self, row) -> List[Dimension]:
        dimensions = []
        if pd.notna(row['width']) and pd.notna(row['height']):
            dimensions.append(Dimension(value=float(row['width']), unit=row['units'], type='width'))
            dimensions.append(Dimension(value=float(row['height']), unit=row['units'], type='height'))
        if pd.notna(row['depth']):
            dimensions.append(Dimension(value=float(row['depth']), unit=row['units'], type='depth'))
        return dimensions


def main():
    processor = TateDataProcessor()
    unified_data = processor.get_unified_data('../data/source_datasets/tate_gallery.csv')

    # Print first 10 records
    for artwork in unified_data[:10]:
        print(artwork)
        print()

    print(len(unified_data))


if __name__ == '__main__':
    main()
