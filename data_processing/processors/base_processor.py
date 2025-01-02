import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
import pandas as pd

from models.data_models import (
    UnifiedArtwork,
    Museum,
    ArtObject,
    Artist,
    Image,
    DateInfo,
    DateType
)

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')


class BaseMuseumDataProcessor(ABC):
    """
    A base processor that uses a 'column_map' to define how each CSV column
    is mapped or parsed into the UnifiedArtwork model.
    """

    # Number of rows to load in dev mode
    DEV_MODE_ROWS = 100

    # Define a basic structure for the column map:
    # {
    #   "id": { "model": "id" },
    #   "title": { "model": "art_object.name" },
    #   "creation_date": { "parse": my_date_parser },
    #   ...
    # }
    #
    # The "model" value is a dotted path telling us which sub-field to fill.
    # The "parse" key can be a custom function that returns a typed value (DateInfo, str, etc.).
    #
    # Alternatively, child classes can override parse methods directly if needed.

    column_map: Dict[str, Dict[str, Any]] = {}

    # If you have columns you *never* want in metadata, place them here
    exclude_from_metadata: Set[str] = set()

    @abstractmethod
    def load_data(self, file_path: str, dev_mode: bool = False) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_museum_name(self) -> str:
        pass

    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
        """
        Convert the DataFrame into a list of UnifiedArtwork objects.
        """
        artworks = []
        for index, row in df.iterrows():
            try:
                artwork = self._row_to_artwork(row, index)
                artworks.append(artwork)
            except Exception as e:
                logging.error(f"Error processing row {row.get('id', index)}: {e}")
        return artworks

    def get_unified_data(self, file_path: str, dev_mode: bool = False) -> List[UnifiedArtwork]:
        df = self.load_data(file_path, dev_mode)
        return self.process_data(df)

    # -----------------------------------------------------------------
    # Core row -> UnifiedArtwork logic
    # -----------------------------------------------------------------
    def _row_to_artwork(self, row: pd.Series, index) -> UnifiedArtwork:
        """
        Create a UnifiedArtwork from a single row using column_map, plus fallback logic.
        """
        # Start with a new instance (we’ll fill it in piecewise)
        artwork = UnifiedArtwork(
            id="",
            museum=Museum(name=self.get_museum_name()),
            object=ArtObject(name="", creation_date=None, type=None),
            artist=Artist(name="Unknown Artist", birth_year=None, death_year=None),
            images=[],
            web_url=None,
            metadata={}
        )

        # 1. Apply the column_map to fill fields
        used_columns = set()

        for col_name, config in self.column_map.items():
            if col_name not in row or pd.isna(row[col_name]):
                logging.debug(f"Row {index}: Skipping column '{col_name}' (missing or NaN).")
                continue

            raw_val = row[col_name]
            used_columns.add(col_name)

            # Parse if necessary
            if "parse" in config and callable(config["parse"]):
                try:
                    parsed_val = config["parse"](raw_val, row)
                    logging.debug(f"Row {index}: Parsed column '{col_name}' value '{raw_val}' to '{parsed_val}'.")
                except Exception as e:
                    logging.error(f"Row {index}: Failed to parse column '{col_name}' with value '{raw_val}': {e}")
                    continue
            else:
                parsed_val = raw_val
                logging.debug(f"Row {index}: Using raw column '{col_name}' value '{raw_val}'.")

            # If there's a "model" path, set that field
            if "model" in config:
                try:
                    self._set_model_field(artwork, config["model"], parsed_val)
                    logging.debug(f"Row {index}: Set '{config['model']}' to '{parsed_val}'.")
                except Exception as e:
                    logging.error(f"Row {index}: Failed to set field '{config['model']}' with value '{parsed_val}': {e}")
                    continue

        # 2. Fill metadata with leftover columns
        artwork.metadata = self._create_metadata(row, used_columns)
        logging.debug(f"Row {index}: Metadata extracted: {artwork.metadata}")

        # 3. If the ID is still empty, try a default from row['id']
        if not artwork.id and "id" in row and pd.notna(row["id"]):
            artwork.id = str(row["id"])
            logging.debug(f"Row {index}: Fallback ID set to '{artwork.id}'.")

        return artwork

    def _set_model_field(self, artwork: UnifiedArtwork, dotted_path: str, value: Any) -> None:
        """
        Sets a field on the artwork given a dotted path like:
          "id" -> artwork.id
          "object.name" -> artwork.object.name
          "artist.name" -> artwork.artist.name
        """
        parts = dotted_path.split(".")
        target = artwork
        for attr in parts[:-1]:
            target = getattr(target, attr)
        setattr(target, parts[-1], value)

    def _create_metadata(self, row: pd.Series, used_columns: set) -> dict:
        """
        Put all columns not in used_columns or exclude_from_metadata into the metadata dict.
        """
        metadata = {}
        for col in row.index:
            if col not in used_columns and col not in self.exclude_from_metadata:
                val = row[col]
                if pd.notna(val):
                    metadata[col] = val
                    logging.debug(f"Row {row.name}: Added '{col}': '{val}' to metadata.")
        return metadata
