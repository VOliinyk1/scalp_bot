from abc import ABC, abstractmethod
import pandas as pd

class MarketDataSource(ABC):
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        ...
    def get_orderbook_imbalance(self, symbol: str) -> float:
        return 0.0
    def get_top_traders_ratio(self, symbol: str) -> float:
        return 0.5
