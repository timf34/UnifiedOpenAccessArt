import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List

from processors.registry import ProcessorRegistry
from models.data_models import UnifiedArtwork

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMerger:
    def __init__(self):
        self.registry = ProcessorRegistry()
        logger.info(f"Found processors for: {self.registry.supported_museums}")

    def flatten_artwork(self, artwork: UnifiedArtwork) -> Dict:
        """Convert a UnifiedArtwork object to a flat dictionary."""
        return {
            'id': artwork.id,
            'museum': artwork.museum.name,
            'title': artwork.object.name,
            'type': artwork.object.type,
            'artist_name': artwork.artist.name,
            'artist_birth': artwork.artist.birth_year,
            'artist_death': artwork.artist.death_year,
            'date_text': artwork.object.creation_date.display_text if artwork.object.creation_date else None,
            'start_year': artwork.object.creation_date.start_year if artwork.object.creation_date else None,
            'end_year': artwork.object.creation_date.end_year if artwork.object.creation_date else None,
            'url': str(artwork.web_url) if artwork.web_url else None,
            'image_url': str(artwork.images[0].url) if artwork.images else None
        }

    def process_museums(self, data_dir: Path) -> None:
        """Process all museum datasets and save to a single CSV."""
        all_artworks = []

        # Process each museum
        for museum in self.registry.supported_museums:
            file_pattern = self.registry.get_source_file_pattern(museum)
            if not file_pattern:
                continue

            file_path = data_dir / file_pattern
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue

            try:
                logger.info(f"Processing {museum}...")
                processor = self.registry.get_processor(museum)
                artworks = processor.get_unified_data(str(file_path), dev_mode=True)
                flattened = [self.flatten_artwork(a) for a in artworks]
                all_artworks.extend(flattened)
                logger.info(f"Added {len(flattened)} artworks from {museum}")
            except Exception as e:
                logger.error(f"Error processing {museum}: {e}")
                continue

        # Save to CSV
        if not all_artworks:
            logger.error("No artworks processed!")
            return

        df = pd.DataFrame(all_artworks)
        output_path = Path('data/processed_datasets/unified_art.csv')
        output_path.parent.mkdir(exist_ok=True)
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(df)} artworks to {output_path}")

        # Print simple stats
        print("\nDataset Statistics:")
        print(f"Total artworks: {len(df):,}")
        print("\nArtworks per museum:")
        print(df['museum'].value_counts().to_string())


def main():
    merger = SimpleMerger()
    merger.process_museums(Path('data/source_datasets'))


if __name__ == "__main__":
    main()