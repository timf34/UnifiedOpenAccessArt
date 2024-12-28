from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, Union
import pandas as pd
from datetime import datetime

from models.data_models import UnifiedArtwork, Artist, Dimension, Image, ArtworkLocation


@dataclass
class ColumnMapping:
    source: str  # Source column name
    target: str  # Target field name in unified schema
    transform: Optional[Callable] = None  # Optional transformation function
    required: bool = False  # Whether the field is required
    default: Any = None  # Default value if source is missing/empty


@dataclass
class NestedMapping:
    target_class: Type  # The class to instantiate (e.g., Artist, Dimension)
    mappings: Dict[str, ColumnMapping]  # Mappings for the nested object's fields
    condition: Optional[Callable] = None  # Optional condition to check if should create object


class DataTransformer:
    """Base class for transforming museum data into unified format."""

    def __init__(self):
        self._column_mappings: Dict[str, Union[ColumnMapping, NestedMapping]] = {}
        self._define_mappings()

    def _define_mappings(self):
        """Override this method to define column mappings."""
        raise NotImplementedError("Must define column mappings")

    def add_mapping(self, mapping: Union[ColumnMapping, NestedMapping]):
        """Add a column mapping."""
        if isinstance(mapping, ColumnMapping):
            self._column_mappings[mapping.target] = mapping
        else:
            self._column_mappings[mapping.target_class.__name__.lower()] = mapping

    def transform(self, df: pd.DataFrame) -> List[Dict]:
        """Transform the input DataFrame using defined mappings."""
        results = []

        for _, row in df.iterrows():
            try:
                transformed = self._transform_row(row)
                if transformed:
                    results.append(transformed)
            except Exception as e:
                print(f"Error transforming row: {e}")
                continue

        return results

    def _transform_row(self, row: pd.Series) -> Optional[Dict]:
        """Transform a single row using the defined mappings."""
        result = {}

        for field, mapping in self._column_mappings.items():
            if isinstance(mapping, ColumnMapping):
                value = self._get_field_value(row, mapping)
                if mapping.required and value is None:
                    return None
                result[field] = value
            elif isinstance(mapping, NestedMapping):
                nested = self._create_nested_object(row, mapping)
                result[field] = nested

        return result

    def _get_field_value(self, row: pd.Series, mapping: ColumnMapping) -> Any:
        """Get value for a field using its mapping."""
        value = row.get(mapping.source, mapping.default)

        if pd.isna(value):
            value = mapping.default

        if value is not None and mapping.transform:
            try:
                value = mapping.transform(value)
            except Exception as e:
                print(f"Error transforming {mapping.source}: {e}")
                value = mapping.default

        return value

    def _create_nested_object(self, row: pd.Series, mapping: NestedMapping) -> Optional[Any]:
        """Create a nested object using its mapping definition."""
        if mapping.condition and not mapping.condition(row):
            return None

        kwargs = {}
        for field, field_mapping in mapping.mappings.items():
            value = self._get_field_value(row, field_mapping)
            kwargs[field] = value

        return mapping.target_class(**kwargs)

def get_safe_value(row, key):
    """Safely get value from row whether it's a dict, Series, or list."""
    if isinstance(row, (dict, pd.Series)):
        return row.get(key) if isinstance(row, dict) else row.get(key, row[key] if key in row else None)
    elif isinstance(row, list) and isinstance(key, int):
        return row[key] if 0 <= key < len(row) else None
    return None


# Example implementation for CMOA
class CMOATransformer(DataTransformer):
    def _define_mappings(self):
        # Date parsing helper functions
        def parse_date_range(date_str):
            if pd.isna(date_str):
                return None
            try:
                # Handle date ranges with '|' separator
                if '|' in str(date_str):
                    return str(date_str).split('|')[0]  # Take the first date
                return str(date_str)
            except Exception:
                return None

        def parse_year_from_string(date_str):
            if pd.isna(date_str):
                return None
            try:
                # Handle date ranges with '|' separator
                if '|' in str(date_str):
                    date_str = str(date_str).split('|')[0]  # Take the first date
                # Extract year from date string
                return int(str(date_str)[:4])
            except Exception:
                return None

        # Basic field mappings
        self.add_mapping(ColumnMapping("id", "id", str, required=True))
        self.add_mapping(ColumnMapping("accession_number", "accession_number", str, required=True))
        self.add_mapping(ColumnMapping("title", "title", required=True))

        # Rights mapping
        self.add_mapping(ColumnMapping(
            source="rights",
            target="rights_and_reproduction",
            default="No known copyright restrictions",
            required=True
        ))

        # Artist mapping with improved date handling
        self.add_mapping(NestedMapping(
            target_class=Artist,
            mappings={
                "name": ColumnMapping(
                    source="cited_name",
                    target="name",
                    transform=lambda x: x if pd.notna(x) else "Unknown",
                    default="Unknown",
                    required=True
                ),
                "birth_date": ColumnMapping(
                    source="birth_date",
                    target="birth_date",
                    transform=parse_date_range,
                    default=None
                ),
                "death_date": ColumnMapping(
                    source="death_date",
                    target="death_date",
                    transform=parse_date_range,
                    default=None
                ),
                "nationality": ColumnMapping("nationality", "nationality", default=None),
                "biography": ColumnMapping("biography", "biography", default=None),
                "role": ColumnMapping("role", "role", default=None)
            }
        ))

        # Dimensions mapping with improved error handling
        def create_dimensions(row):
            dimensions = []
            dimension_fields = {
                'item_width': 'width',
                'item_height': 'height',
                'item_depth': 'depth',
                'item_diameter': 'diameter'
            }

            try:
                for field, dim_type in dimension_fields.items():
                    value = get_safe_value(row, field)
                    if pd.notna(value):
                        try:
                            float_value = float(value)
                            if float_value > 0:
                                dimensions.append(Dimension(
                                    value=float_value,
                                    unit='inches',
                                    type=dim_type
                                ))
                        except (ValueError, TypeError):
                            continue
            except Exception as e:
                print(f"Error processing dimensions: {str(e)}")
            return dimensions

        self.add_mapping(ColumnMapping(
            source='',
            target='dimensions',
            transform=create_dimensions,
            default=[]
        ))

        # Images mapping with improved error handling
        def create_images(row):
            images = []
            try:
                image_url = get_safe_value(row, 'image_url')
                web_url = get_safe_value(row, 'web_url')

                if pd.notna(image_url):
                    images.append(Image(
                        url=image_url,
                        copyright=None,
                        type='primary'
                    ))
                if pd.notna(web_url):
                    images.append(Image(
                        url=web_url,
                        copyright=None,
                        type='web'
                    ))
            except Exception as e:
                print(f"Error processing images: {str(e)}")
            return images

        self.add_mapping(ColumnMapping(
            source='',
            target='images',
            transform=create_images,
            default=[]
        ))

        # Location mapping
        self.add_mapping(NestedMapping(
            target_class=ArtworkLocation,
            mappings={
                "gallery": ColumnMapping("gallery", "gallery", default=None),
                "room": ColumnMapping("room", "room", default=None),
                "wall": ColumnMapping("wall", "wall", default=None),
                "current_location": ColumnMapping("physical_location", "current_location", default=None)
            }
        ))

        # Date fields with improved parsing
        self.add_mapping(ColumnMapping("creation_date", "date_created", default=None))
        self.add_mapping(ColumnMapping(
            "creation_date_earliest",
            "date_start",
            transform=parse_year_from_string,
            default=None
        ))
        self.add_mapping(ColumnMapping(
            "creation_date_latest",
            "date_end",
            transform=parse_year_from_string,
            default=None
        ))

        # Additional fields
        self.add_mapping(ColumnMapping("medium", "medium", default=None))
        self.add_mapping(ColumnMapping("credit_line", "credit_line", default=None))
        self.add_mapping(ColumnMapping("department", "department", default=None))
        self.add_mapping(ColumnMapping("classification", "classification", default=None))
        self.add_mapping(ColumnMapping("object_type", "object_type", default=None))
        self.add_mapping(ColumnMapping("culture", "culture", default=None))
        self.add_mapping(ColumnMapping("period", "period", default=None))
        self.add_mapping(ColumnMapping("dynasty", "dynasty", default=None))
        self.add_mapping(ColumnMapping("description", "description", default=None))
        self.add_mapping(ColumnMapping("exhibition_history", "exhibition_history", default=None))
        self.add_mapping(ColumnMapping("bibliography", "bibliography", default=None))
        self.add_mapping(ColumnMapping("url", "url", default=None))

        # Constant values
        self.add_mapping(ColumnMapping(
            source="",
            target="source_museum",
            default="Carnegie Museum of Art",
            required=True
        ))
        self.add_mapping(ColumnMapping(
            source="",
            target="is_public_domain",
            default=True,
            required=True
        ))
        self.add_mapping(ColumnMapping(
            source="",
            target="provenance",
            default=[],
            required=True
        ))

    def _get_field_value(self, row: pd.Series, mapping: ColumnMapping) -> Any:
        """Get value for a field using its mapping."""
        if not mapping.source:  # Handle empty source fields
            value = mapping.default
        else:
            value = get_safe_value(row, mapping.source)

        if pd.isna(value):
            value = mapping.default

        if value is not None and mapping.transform:
            try:
                value = mapping.transform(value)
            except Exception as e:
                print(f"Error transforming {mapping.source}: {str(e)}")
                value = mapping.default

        return value

    def transform(self, df: pd.DataFrame) -> List[dict]:
        results = []
        for _, row in df.iterrows():
            try:
                # Convert row to dictionary first
                row_dict = row.to_dict() if isinstance(row, pd.Series) else row

                transformed = self._transform_row(row_dict)
                if transformed:
                    # Store original data
                    transformed['original_metadata'] = row_dict

                    # Ensure all required fields have defaults
                    transformed.setdefault('rights_and_reproduction', 'No known copyright restrictions')
                    transformed.setdefault('provenance', [])
                    transformed.setdefault('images', [])
                    transformed.setdefault('dimensions', [])

                    if 'location' not in transformed:
                        transformed['location'] = ArtworkLocation(
                            gallery=None,
                            room=None,
                            wall=None,
                            current_location=None
                        )

                    # Create UnifiedArtwork instance
                    artwork = UnifiedArtwork(**transformed)
                    results.append(artwork.dict())
            except Exception as e:
                print(f"Error transforming row: {str(e)}")
                continue
        return results


# Example usage
def process_museum_data(file_path: str, transformer: DataTransformer) -> List[Dict]:
    """Process museum data using the provided transformer."""
    df = pd.read_csv(file_path)
    return transformer.transform(df)


# Helper functions for common transformations
def parse_date(date_str: str) -> Optional[int]:
    """Parse a date string into a year."""
    if pd.isna(date_str):
        return None
    try:
        return pd.to_datetime(date_str).year
    except Exception:
        return None


def split_dimension(dim_str: str) -> Optional[float]:
    """Extract numeric value from dimension string."""
    if pd.isna(dim_str):
        return None
    try:
        return float(''.join(c for c in dim_str if c.isdigit() or c == '.'))
    except ValueError:
        return None


def main():
    cmoa_transformer = CMOATransformer()
    cmoa_data = process_museum_data('../../data/source_datasets/cmoa.csv', cmoa_transformer)
    print(f"CMOA data: {cmoa_data[:2]}")


if __name__ == "__main__":
    main()