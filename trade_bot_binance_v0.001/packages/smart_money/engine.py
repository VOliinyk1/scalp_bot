import time
import pandas as pd
from datetime import datetime, timedelta
from .features import add_returns, rolling_stats, enrich_with_sm_signals, build_feature_matrix
from .labeling import make_labels
from packages.data.binance import DummyBinance
from packages.core.config import settings

class SmartMoneyEngine:
    def __init__(self, datasource=None):
        self.ds = datasource or DummyBinance()
        self.last_train_at = None
        self.retrain_every = timedelta(hours=6)

    def _need_retrain(self) -> bool:
        if self.last_train_at is None:
            return True
        return (datetime.utcnow() - self.last_train_at) >= self.retrain_every

    def train_if_needed(self):
        if not self._need_retrain():
            return
        df = self.ds.get_ohlcv(settings.SYMBOL, settings.TIMEFRAME, limit=1200)
        df = add_returns(df)
        df = rolling_stats(df, window=20)
        ob = self.ds.get_orderbook_imbalance(settings.SYMBOL)
        tr = self.ds.get_top_traders_ratio(settings.SYMBOL)
        df = enrich_with_sm_signals(df, ob, tr)
        X = build_feature_matrix(df)
        y = make_labels(df)
        # TODO: fit model & persist (skipped in this scaffold)
        self.last_train_at = datetime.utcnow()

    def latest_signal(self):
        self.train_if_needed()
        df = self.ds.get_ohlcv(settings.SYMBOL, settings.TIMEFRAME, limit=200)
        df = add_returns(df)
        df = rolling_stats(df, window=20)
        ob = self.ds.get_orderbook_imbalance(settings.SYMBOL)
        tr = self.ds.get_top_traders_ratio(settings.SYMBOL)
        df = enrich_with_sm_signals(df, ob, tr)
        X_live = build_feature_matrix(df).tail(1)

        # Placeholder probs; replace with real model.predict_proba(X_live)
        p_buy = float(min(max(0.5 + (tr-0.5) + ob*0.1, 0.0), 1.0))
        p_sell = float(1.0 - p_buy)

        signal = "HOLD"
        if p_buy >= 0.6:
            signal = "BUY"
        elif p_sell >= 0.6:
            signal = "SELL"

        return {
            "symbol": settings.SYMBOL,
            "timeframe": settings.TIMEFRAME,
            "p_buy": round(p_buy, 4),
            "p_sell": round(p_sell, 4),
            "signal": signal,
            "ob_imbalance": ob,
            "top_traders_ratio": tr,
            "ts": int(time.time()*1000)
        }
