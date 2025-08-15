# app/services/smart_money.py
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib

from app.services.binance_api import BinanceAPI as binance_api


# -------------------------------------------------------
# Конфіг (за замовчуванням; можна читати з env/.env)
# -------------------------------------------------------

@dataclass
class SMConfig:
    symbol: str = os.getenv("SM_SYMBOL", "BTCUSDT")
    timeframe: str = os.getenv("SM_TIMEFRAME", "5m")  # "1m","5m","15m","1h"
    horizon_bars: int = int(os.getenv("SM_HORIZON_BARS", "12"))  # 12*5m ≈ 1 год
    pos_label_threshold: float = float(os.getenv("SM_POS_TH", "0.002"))  # +0.2%
    neg_label_threshold: float = float(os.getenv("SM_NEG_TH", "-0.002")) # -0.2%
    min_features_window: int = int(os.getenv("SM_MIN_F_WIN", "50"))
    retrain_every_hours: int = int(os.getenv("SM_RETRAIN_HOURS", "6"))
    model_path: str = os.getenv("SM_MODEL_PATH", "models/smart_money.pkl")

CFG = SMConfig()

# -------------------------------------------------------
# Фічі
# -------------------------------------------------------

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """ Обчислює RSI (Relative Strength Index) для серії цін. """
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = up / (down + 1e-12)
    return 100 - (100 / (1 + rs))

def rsi_z(series: pd.Series, period: int = 20) -> pd.Series:
    ''' Обчислює Z-скор для RSI.'''
    rsi_values = rsi(series, period)
    return (rsi_values - rsi_values.rolling(window=period).mean()) / rsi_values.rolling(window=period).std()

def ema(series: pd.Series, period: int) -> pd.Series:
    ''' Обчислює експоненціальне ковзне середнє (EMA) для серії цін.'''
    return series.ewm(span=period, adjust=False).mean()

def macd(series: pd.Series, short_period: int = 12, long_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
    ''' Обчислює MACD (Moving Average Convergence Divergence) для серії цін.'''
    ema_short = ema(series, short_period)
    ema_long = ema(series, long_period)
    macd_line = ema_short - ema_long
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    return pd.DataFrame({
        "macd": macd_line,
        "macd_signal": signal_line
    })

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ Обчислює ADX (Average Directional Index) для серії цін. """
    df = df.copy()
    df["tr"] = atr(df, period)
    df["+dm"] = np.where((df["high"].diff() > df["low"].diff()) & (df["high"].diff() > 0), df["high"].diff(), 0)
    df["-dm"] = np.where((df["low"].diff() > df["high"].diff()) & (df["low"].diff() > 0), df["low"].diff(), 0)
    df["+di"] = 100 * (df["+dm"].ewm(alpha=1/period, adjust=False).mean() / df["tr"])
    df["-di"] = 100 * (df["-dm"].ewm(alpha=1/period, adjust=False).mean() / df["tr"])
    adx = 100 * (abs(df["+di"] - df["-di"]) / (df["+di"] + df["-di"])).ewm(alpha=1/period, adjust=False).mean()
    return adx

def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ret1"] = df["close"].pct_change()
    df["ret5"] = df["close"].pct_change(5)
    df["ret20"] = df["close"].pct_change(20)
    return df

def rolling_stats(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    df = df.copy()
    df["volat"] = df["close"].pct_change().rolling(window).std()
    df["rsi"] = rsi(df["close"], window)
    df["atr"] = atr(df, window)
    return df

def enrich_with_sm_signals(
    df: pd.DataFrame,
    ob_imbalance: float,
    top_ratio: float,
    news_sent: Optional[float] = None
) -> pd.DataFrame:
    """ Додаємо Smart Money ознаки (дисбаланс книги заявок, топ-трейдери, новини). """
    df = df.copy()
    df["ob_imbalance"] = ob_imbalance
    df["top_ratio"] = top_ratio
    df["mom5"] = df["close"].pct_change(5)
    df["mom20"] = df["close"].pct_change(20)
    if news_sent is not None:
        df["news_sentiment"] = float(np.clip(news_sent, -1, 1))
    else:
        df["news_sentiment"] = 0.0
    return df

def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "ret1","ret5","ret20",
        "volat","rsi","rsi_z","ema","macd","adx","atr",
        "ob_imbalance","top_ratio","mom5","mom20",
        "volume","news_sentiment"
    ]
    mat = df[cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return mat

# -------------------------------------------------------
# Лейблінг для тренування
# -------------------------------------------------------

def make_labels(df: pd.DataFrame) -> pd.Series:
    """ 1 = BUY, -1 = SELL, 0 = NO-TRADE за майбутнім доходом на CFG.horizon_bars """
    future = df["close"].shift(-CFG.horizon_bars)
    ret = (future / df["close"] - 1.0)
    y = (ret >= CFG.pos_label_threshold).astype(int) - (ret <= CFG.neg_label_threshold).astype(int)
    return y.fillna(0)

# -------------------------------------------------------
# Модель
# -------------------------------------------------------

class SMLRModel:
    """ Простий пайплайн: StandardScaler + LogisticRegression (бінарно BUY vs інше). """
    def __init__(self, model_path: str = CFG.model_path):
        self.model_path = model_path
        self.pipe: Pipeline = Pipeline([
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("clf", LogisticRegression(max_iter=400, n_jobs=None, multi_class="ovr"))
        ])

    def fit(self, X: pd.DataFrame, y_multi: pd.Series):
        # Тренуємо на бінарний таргет BUY vs not-BUY.
        y = (y_multi == 1).astype(int)
        self.pipe.fit(X, y)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.pipe.predict_proba(X)[:, 1]  # ймовірність класу BUY

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.pipe, self.model_path)

    def load(self) -> None:
        self.pipe = joblib.load(self.model_path)

# -------------------------------------------------------
# Джерела даних (інтерфейси)
# -------------------------------------------------------

class MarketDataSource:
    """ Мінімальний інтерфейс, сумісний з твоїм services/binance_api.py """
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        raise NotImplementedError

    def get_orderbook_imbalance(self, symbol: str) -> float:
        return 0.0

    def get_top_traders_ratio(self, symbol: str) -> float:
        return 0.5

class DummyData(MarketDataSource):
    """ Заглушка — якщо твій binance_api ще не підключено тут. """
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        now = int(time.time() // 60 * 60) * 1000
        idx = pd.date_range(end=pd.to_datetime(now, unit="ms"), periods=limit, freq="5min")
        base = np.cumsum(np.random.randn(limit) * 5) + 60000
        close = base + np.random.randn(limit)
        high = close + np.abs(np.random.randn(limit) * 5)
        low  = close - np.abs(np.random.randn(limit) * 5)
        open_ = close + np.random.randn(limit)
        vol = np.abs(np.random.randn(limit) * 50_000)
        return pd.DataFrame({
            "ts": (idx.astype("int64") // 10**6),
            "open": open_, "high": high, "low": low, "close": close, "volume": vol
        })

class BinanceData(MarketDataSource):
    """ Реалізація для Binance API, адаптуй під свій binance_api.py. """

    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        df = 
# -------------------------------------------------------
# Інтеграції з твоїми модулями (опційно, якщо є)
# -------------------------------------------------------

def maybe_get_news_sentiment(symbol: str) -> Optional[float]:
    """
    Якщо у тебе є app/services/new_sentiment.py з функцією get_sentiment(symbol) -> float[-1..1],
    підключи його тут і поверни значення. Якщо немає — лишаємо None.
    """
    try:
        from .new_sentiment import get_sentiment  # адаптуй під свою сигнатуру
        return float(get_sentiment(symbol))
    except Exception:
        return None

# -------------------------------------------------------
# Двигун Smart Money
# -------------------------------------------------------

class SmartMoneyEngine:
    def __init__(self, datasource: Optional[MarketDataSource] = None, model_path: Optional[str] = None):
        self.ds: MarketDataSource = datasource or DummyData()
        self.model = SMLRModel(model_path or CFG.model_path)
        self.last_train_at: Optional[datetime] = None
        self.retrain_every = timedelta(hours=CFG.retrain_every_hours)

    # ---- внутрішні утиліти

    def _fetch_df(self, symbol: str, timeframe: str, limit: int = 1200) -> pd.DataFrame:
        df = self.ds.get_ohlcv(symbol, timeframe, limit=limit)
        # Переконайся, що є всі обов’язкові колонки:
        need = {"ts","open","high","low","close","volume"}
        miss = need - set(df.columns)
        if miss:
            raise ValueError(f"OHLCV is missing columns: {miss}")
        return df.sort_values("ts").reset_index(drop=True)

    def _need_retrain(self) -> bool:
        if self.last_train_at is None:
            return True
        return (datetime.utcnow() - self.last_train_at) >= self.retrain_every

    # ---- публічні методи

    def train_if_needed(self) -> None:
        if not self._need_retrain():
            return

        df = self._fetch_df(CFG.symbol, CFG.timeframe, limit=1200)
        df = add_returns(df)
        df = rolling_stats(df, window=20)

        ob = self.ds.get_orderbook_imbalance(CFG.symbol)
        tr = self.ds.get_top_traders_ratio(CFG.symbol)
        news = maybe_get_news_sentiment(CFG.symbol)

        df = enrich_with_sm_signals(df, ob, tr, news_sent=news)

        # матриця фіч та лейбли
        X = build_feature_matrix(df)
        y = make_labels(df)

        # Відкидаємо хвости без майбутнього й прогріваючі вікна
        min_idx = max(20, CFG.min_features_window)
        X = X.iloc[min_idx:-CFG.horizon_bars]
        y = y.iloc[min_idx:-CFG.horizon_bars]
        if len(X) < 200:
            # надто мало даних — переносимо тренування
            self.last_train_at = datetime.utcnow()
            return

        self.model.fit(X, y)
        self.model.save()
        self.last_train_at = datetime.utcnow()

    def latest_signal(self) -> Dict[str, Any]:
        """ Прогноз на останню свічку; повертає словник зі `signal`, `p_buy`, `p_sell` тощо. """
        # 1) тренування за потреби
        self.train_if_needed()

        # 2) live-фічі
        df = self._fetch_df(CFG.symbol, CFG.timeframe, limit=200)
        df = add_returns(df)
        df = rolling_stats(df, window=20)

        ob = self.ds.get_orderbook_imbalance(CFG.symbol)
        tr = self.ds.get_top_traders_ratio(CFG.symbol)
        news = maybe_get_news_sentiment(CFG.symbol)

        df = enrich_with_sm_signals(df, ob, tr, news_sent=news)
        X_live = build_feature_matrix(df).tail(1)

        # 3) p_buy/p_sell
        try:
            self.model.load()
            p_buy = float(self.model.predict_proba(X_live)[0])
        except Exception:
            # якщо модель ще не натренована або файл відсутній — використовуй просту евристику
            p_buy = float(np.clip(0.5 + (tr - 0.5) + ob * 0.1 + (news or 0)*0.05, 0.0, 1.0))

        p_sell = float(1.0 - p_buy)

        # 4) дискретний сигнал
        signal = "HOLD"
        if p_buy >= 0.6:
            signal = "BUY"
        elif p_sell >= 0.6:
            signal = "SELL"

        return {
            "symbol": CFG.symbol,
            "timeframe": CFG.timeframe,
            "p_buy": round(p_buy, 4),
            "p_sell": round(p_sell, 4),
            "signal": signal,
            "ob_imbalance": float(ob),
            "top_traders_ratio": float(tr),
            "news_sentiment": float(news) if news is not None else 0.0,
            "ts": int(time.time() * 1000),
        }
