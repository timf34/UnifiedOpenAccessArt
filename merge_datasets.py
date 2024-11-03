import pandas as pd
from typing import Dict
from pathlib import Path
import logging
from datetime import datetime

from processors import ProcessorRegistry
from models.data_models import UnifiedArtwork

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetMerger:
    def __init__(self):
        self.registry = ProcessorRegistry()
        logger.info(f"Initialized merger with support for museums: {self.registry.supported_museums}")

    def flatten_artwork(self, artwork: UnifiedArtwork) -> Dict:
        """Flatten a UnifiedArtwork object into a dictionary suitable for CSV conversion."""
        flat_dict = {
            'id': artwork.id,
            'accession_number': artwork.accession_number,
            'title': artwork.title,
            'source_museum': artwork.source_museum,

            # Artist information
            'artist_name': artwork.artist.name if artwork.artist else None,
            'artist_birth_date': artwork.artist.birth_date if artwork.artist else None,
            'artist_death_date': artwork.artist.death_date if artwork.artist else None,
            'artist_nationality': artwork.artist.nationality if artwork.artist else None,
            'artist_role': artwork.artist.role if artwork.artist else None,

            # Dates
            'date_created': artwork.date_created,
            'date_start': artwork.date_start,
            'date_end': artwork.date_end,

            # Basic artwork information
            'medium': artwork.medium,
            'credit_line': artwork.credit_line,
            'department': artwork.department,
            'classification': artwork.classification,
            'object_type': artwork.object_type,
            'culture': artwork.culture,
            'period': artwork.period,
            'dynasty': artwork.dynasty,

            # Text fields
            'description': artwork.description,
            'exhibition_history': artwork.exhibition_history,
            'bibliography': artwork.bibliography,

            # Rights and URLs
            'is_public_domain': artwork.is_public_domain,
            'rights_and_reproduction': artwork.rights_and_reproduction,
            'url': artwork.url,
        }

        # Handle dimensions
        for dim in artwork.dimensions:
            prefix = f'dimension_{dim.type}'
            flat_dict[f'{prefix}_value'] = dim.value
            flat_dict[f'{prefix}_unit'] = dim.unit

        # Handle primary image
        if artwork.images:
            primary_image = artwork.images[0]  # Take first image as primary
            flat_dict.update({
                'primary_image_url': primary_image.url,
                'primary_image_copyright': primary_image.copyright,
            })

        # Handle location
        if artwork.location:
            flat_dict.update({
                'location_gallery': artwork.location.gallery,
                'location_room': artwork.location.room,
                'location_wall': artwork.location.wall,
                'current_location': artwork.location.current_location,
            })

        return flat_dict

    def process_museum_data(self, source_dir: Path) -> pd.DataFrame:
        """Process data from all supported museums and combine into a single DataFrame."""
        all_artworks = []

        for museum_name in self.registry.supported_museums:
            try:
                processor = self.registry.get_processor(museum_name)
                if not processor:
                    logger.warning(f"No processor found for {museum_name}")
                    continue

                file_pattern = f"*{museum_name}*.csv"
                matching_files = list(source_dir.glob(file_pattern))

                if not matching_files:
                    logger.warning(f"No matching files found for {museum_name}")
                    continue

                file_path = str(matching_files[0])
                logger.info(f"Processing {museum_name} data from {file_path}")

                unified_artworks = processor.get_unified_data(file_path)
                all_artworks.extend([self.flatten_artwork(artwork) for artwork in unified_artworks])

                logger.info(f"Processed {len(unified_artworks)} artworks from {museum_name}")

            except Exception as e:
                logger.error(f"Error processing {museum_name} data: {str(e)}")
                continue

        return pd.DataFrame(all_artworks)

    def save_merged_dataset(self, df: pd.DataFrame, output_dir: Path, format: str = 'csv') -> None:
        """Save the merged dataset in the specified format."""
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d')
        output_path = output_dir / f"unified_museum_data_{timestamp}.{format}"

        if format == 'csv':
            df.to_csv(output_path, index=False, encoding='utf-8')
        elif format == 'parquet':
            df.to_parquet(output_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {format}")

        logger.info(f"Saved merged dataset to {output_path}")

        # Save column documentation
        docs_path = output_dir / f"column_documentation_{timestamp}.md"
        with open(docs_path, 'w', encoding='utf-8') as f:
            f.write("# Unified Museum Dataset Column Documentation\n\n")
            for col in df.columns:
                f.write(f"## {col}\n")
                f.write(f"- Type: {df[col].dtype}\n")
                f.write(f"- Non-null count: {df[col].count()}\n")
                f.write(f"- Sample values: {df[col].dropna().head(3).tolist()}\n\n")


def main():
    # Set up paths
    base_dir = Path(__file__).parent
    source_dir = base_dir / "data" / "source_datasets"
    output_dir = base_dir / "data" / "processed_datasets"

    # Initialize and run merger
    merger = DatasetMerger()

    try:
        # Process and merge datasets
        logger.info("Starting dataset merge process...")
        merged_df = merger.process_museum_data(source_dir)

        # Save results
        merger.save_merged_dataset(merged_df, output_dir, format='csv')
        merger.save_merged_dataset(merged_df, output_dir, format='parquet')

        logger.info(f"Successfully processed {len(merged_df)} total artworks")

    except Exception as e:
        logger.error(f"Error during merge process: {str(e)}")
        raise


if __name__ == "__main__":
    main()
