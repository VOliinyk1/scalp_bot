import pandas as pd, numpy as np, time
from .base import MarketDataSource

class DummyBinance(MarketDataSource):
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        now = int(time.time() // 60 * 60) * 1000
        idx = pd.date_range(end=pd.to_datetime(now, unit='ms'), periods=limit, freq="5min")
        base = np.cumsum(np.random.randn(limit) * 5) + 60000
        close = base + np.random.randn(limit)
        high = close + np.abs(np.random.randn(limit) * 5)
        low  = close - np.abs(np.random.randn(limit) * 5)
        open_ = close + np.random.randn(limit)
        vol = np.abs(np.random.randn(limit) * 50_000)
        df = pd.DataFrame({
            "ts": (idx.astype("int64") // 10**6),
            "open": open_, "high": high, "low": low, "close": close, "volume": vol
        })
        return df

    def get_orderbook_imbalance(self, symbol: str) -> float:
        return float(np.clip(np.random.randn() * 0.2, -1, 1))

    def get_top_traders_ratio(self, symbol: str) -> float:
        return float(np.clip(0.5 + np.random.randn()*0.05, 0, 1))
