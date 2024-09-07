from abc import ABC, abstractmethod
import pandas as pd

from data_models import UnifiedArtworkData


class MuseumDataProcessor(ABC):
    @abstractmethod
    def load_data(self, file_path: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def process_data(self, df: pd.DataFrame) -> list[UnifiedArtworkData]:
        pass

    def get_unified_data(self, file_path: str) -> list[UnifiedArtworkData]:
        df = self.load_data(file_path)
        return self.process_data(df)