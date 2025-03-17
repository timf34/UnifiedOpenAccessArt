from typing import Dict, Optional
from pathlib import Path
import importlib
import logging
import sys
import os

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from data_processing.processors.base_processor import BaseMuseumDataProcessor

# Configure logging to show debug messages
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ProcessorRegistry:
    """Registry for museum data processors with explicit file mappings."""

    # Mapping of processor module names to their source file patterns
    FILE_MAPPINGS = {
        'cleveland_art': 'cleveland_museum_of_art.csv',
        'moma': 'moma.csv',
        'national_gallery_art_dc': 'national_gallery_of_art_dc.csv',
        'cmoa': 'cmoa.csv',
    }

    def __init__(self):
        self._processors: Dict[str, BaseMuseumDataProcessor] = {}
        self._load_processors()

    def _load_processors(self) -> None:
        """Automatically load all processor classes from the processors directory."""
        processors_dir = Path(__file__).parent / "processors"
        logger.debug(f"Looking for processors in directory: {processors_dir}")

        # Skip certain files
        skip_files = {'__init__.py', 'base_processor.py', 'registry.py'}

        # Find all Python files in the processors directory
        processor_files = [f for f in processors_dir.glob("*_processor.py")
                           if f.name not in skip_files]
        logger.debug(f"Found processor files: {[f.name for f in processor_files]}")

        for file_path in processor_files:
            try:
                # Get the module name without '_processor.py'
                museum_name = file_path.stem.replace('_processor', '')
                logger.debug(f"Processing museum: {museum_name}")

                # Skip if we don't have a file mapping for this processor
                if museum_name not in self.FILE_MAPPINGS:
                    logger.warning(f"No file mapping found for {museum_name}, skipping")
                    continue

                # Import the module using absolute path
                module_name = f"data_processing.processors.{file_path.stem}"
                logger.debug(f"Importing module: {module_name}")
                module = importlib.import_module(module_name)

                # Find processor class in the module
                processor_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                            issubclass(attr, BaseMuseumDataProcessor) and
                            attr != BaseMuseumDataProcessor):
                        processor_class = attr
                        logger.debug(f"Found processor class: {attr.__name__}")
                        break

                if processor_class is None:
                    logger.warning(f"No processor class found in {file_path}")
                    continue

                # Initialize the processor
                processor = processor_class()
                self._processors[museum_name] = processor
                logger.info(f"Loaded processor for museum: {museum_name}")

            except Exception as e:
                logger.error(f"Error loading processor from {file_path}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())

    def get_processor(self, museum_name: str) -> Optional[BaseMuseumDataProcessor]:
        """Get a processor by museum name."""
        processor = self._processors.get(museum_name)
        if processor is None:
            logger.warning(f"No processor found for museum: {museum_name}")
        return processor

    def get_source_file_pattern(self, museum_name: str) -> Optional[str]:
        """Get the source file pattern for a museum."""
        pattern = self.FILE_MAPPINGS.get(museum_name)
        if pattern is None:
            logger.warning(f"No file pattern found for museum: {museum_name}")
        return pattern

    def get_all_processors(self) -> Dict[str, BaseMuseumDataProcessor]:
        """Get all registered processors."""
        return self._processors

    @property
    def supported_museums(self) -> list[str]:
        """Get list of supported museum names."""
        return list(self._processors.keys())
    

if __name__ == "__main__":
    registry = ProcessorRegistry()
    print(registry.supported_museums) 