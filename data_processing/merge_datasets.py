import pandas as pd
import sqlite3
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

    def save_to_sqlite(self, df: pd.DataFrame, db_path: Path) -> None:
        """Save the DataFrame to SQLite with proper indexing."""
        logger.info("Saving to SQLite database...")

        with sqlite3.connect(db_path) as conn:
            # Save the data
            df.to_sql('artworks', conn, if_exists='replace', index=False)

            # Create indexes for common queries
            cursor = conn.cursor()
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_museum ON artworks(museum)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_artist ON artworks(artist_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_year ON artworks(start_year)')

            # Create a few example views for common queries
            cursor.execute('''
                CREATE VIEW IF NOT EXISTS artwork_counts_by_museum AS
                SELECT museum, COUNT(*) as artwork_count
                FROM artworks
                GROUP BY museum
            ''')

            cursor.execute('''
                CREATE VIEW IF NOT EXISTS artworks_with_images AS
                SELECT *
                FROM artworks
                WHERE image_url IS NOT NULL
            ''')

            conn.commit()

    def process_museums(self, data_dir: Path) -> None:
        """Process all museum datasets and save to CSV and SQLite."""
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

        # Save results
        if not all_artworks:
            logger.error("No artworks processed!")
            return

        df = pd.DataFrame(all_artworks)

        # Save to CSV
        csv_path = Path('../data/processed_datasets/unified_art.csv')
        csv_path.parent.mkdir(exist_ok=True)
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved {len(df)} artworks to {csv_path}")

        # Save to SQLite
        db_path = Path('../data/processed_datasets/unified_art.db')
        self.save_to_sqlite(df, db_path)
        logger.info(f"Saved to SQLite database at {db_path}")

        # Print simple stats
        print("\nDataset Statistics:")
        print(f"Total artworks: {len(df):,}")
        print("\nArtworks per museum:")
        print(df['museum'].value_counts().to_string())

        # Print example queries
        print("\nExample SQLite queries you can run:")
        print("""
        # Count artworks by museum:
        SELECT * FROM artwork_counts_by_museum;

        # Find all artworks by a specific artist:
        SELECT * FROM artworks WHERE artist_name LIKE '%Van Gogh%';

        # Count artworks with images by museum:
        SELECT museum, COUNT(*) as count 
        FROM artworks_with_images 
        GROUP BY museum;
        """)


def main():
    merger = SimpleMerger()
    merger.process_museums(Path('../data/source_datasets'))


if __name__ == "__main__":
    main()