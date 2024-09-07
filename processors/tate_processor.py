import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List

from data_models import UnifiedArtworkData
from processors.base_processor import MuseumDataProcessor
from utils import clean_text, validate_url


class TateDataProcessor(MuseumDataProcessor):
    def load_data(self, file_path: str) -> pd.DataFrame:
        return pd.read_csv(file_path, low_memory=False)

    def process_data(self, df: pd.DataFrame) -> list[UnifiedArtworkData]:
        unified_data = []
        for _, row in df.iterrows():
            try:
                artwork = self.process_row(row)
                if artwork:
                    unified_data.append(artwork)
            except Exception as e:
                print(f"Error processing row: {row['id']}. Error: {str(e)}")
        return unified_data

    def process_row(self, row: pd.Series) -> UnifiedArtworkData:
        # Data cleaning and validation
        title = clean_text(row['title'])
        artist = clean_text(row['artist'])
        date = self.clean_date(row['dateText'])
        medium = clean_text(row['medium'])
        dimensions = self.clean_dimensions(row['dimensions'])
        credit_line = clean_text(row['creditLine'])
        accession_number = clean_text(row['accession_number'])
        url = validate_url(row['url'])
        image_url = validate_url(row['thumbnailUrl'])

        # Create UnifiedArtworkData object
        artwork = UnifiedArtworkData(
            id=str(row['id']),
            title=title,
            artist=artist,
            date=date,
            medium=medium,
            dimensions=dimensions,
            credit_line=credit_line,
            accession_number=accession_number,
            url=url,
            image_url=image_url
        )

        return artwork

    def clean_date(self, date_text: str) -> Optional[str]:
        if pd.isna(date_text) or date_text == 'date not known':
            return None
        try:
            # Try to parse the date and format it consistently
            parsed_date = datetime.strptime(date_text, "%Y")
            return parsed_date.strftime("%Y")
        except ValueError:
            # If parsing fails, return the original text
            return clean_text(date_text)

    def clean_dimensions(self, dimensions: str) -> Optional[str]:
        if pd.isna(dimensions):
            return None
        # Remove 'support: ' prefix if present
        dimensions = dimensions.replace('support: ', '')
        # Convert to lowercase and remove extra spaces
        return ' '.join(dimensions.lower().split())