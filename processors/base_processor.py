import pandas as pd

from abc import ABC, abstractmethod
from typing import List

from models.data_models import UnifiedArtwork


class BaseMuseumDataProcessor(ABC):
    @abstractmethod
    def load_data(self, file_path: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def process_data(self, df: pd.DataFrame) -> List[UnifiedArtwork]:
        pass

    def get_unified_data(self, file_path: str) -> List[UnifiedArtwork]:
        df = self.load_data(file_path)
        return self.process_data(df)