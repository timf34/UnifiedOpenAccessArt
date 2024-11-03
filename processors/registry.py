from typing import Dict, Type
from pathlib import Path
import importlib
import logging
from .base_processor import BaseMuseumDataProcessor

logger = logging.getLogger(__name__)


class ProcessorRegistry:
    """Registry for museum data processors that automatically discovers and loads processor classes."""

    def __init__(self):
        self._processors: Dict[str, BaseMuseumDataProcessor] = {}
        self._load_processors()

    def _load_processors(self) -> None:
        """Automatically load all processor classes from the processors directory."""
        processors_dir = Path(__file__).parent

        # Skip certain files
        skip_files = {'__init__.py', 'base_processor.py', 'registry.py'}

        # Find all Python files in the processors directory
        processor_files = [f for f in processors_dir.glob("*.py")
                           if f.name not in skip_files]

        for file_path in processor_files:
            try:
                # Import the module
                module_name = f"processors.{file_path.stem}"
                module = importlib.import_module(module_name)

                # Find processor class in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                            issubclass(attr, BaseMuseumDataProcessor) and
                            attr != BaseMuseumDataProcessor):
                        # Initialize the processor
                        processor = attr()
                        museum_name = attr_name.lower().replace('dataprocessor', '')
                        self._processors[museum_name] = processor
                        logger.info(f"Loaded processor: {attr_name}")

            except Exception as e:
                logger.error(f"Error loading processor from {file_path}: {str(e)}")

    def get_processor(self, museum_name: str) -> BaseMuseumDataProcessor:
        """Get a processor by museum name."""
        return self._processors.get(museum_name)

    def get_all_processors(self) -> Dict[str, BaseMuseumDataProcessor]:
        """Get all registered processors."""
        return self._processors

    @property
    def supported_museums(self) -> list:
        """Get list of supported museum names."""
        return list(self._processors.keys())
