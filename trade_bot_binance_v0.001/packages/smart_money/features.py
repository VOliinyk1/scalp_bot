import pandas as pd
import numpy as np

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

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = up / (down + 1e-12)
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def enrich_with_sm_signals(df: pd.DataFrame, ob_imbalance: float, top_ratio: float) -> pd.DataFrame:
    df = df.copy()
    df["ob_imbalance"] = ob_imbalance
    df["top_ratio"] = top_ratio
    df["mom5"] = df["close"].pct_change(5)
    df["mom20"] = df["close"].pct_change(20)
    return df

def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["ret1","ret5","ret20","volat","rsi","atr","ob_imbalance","top_ratio","mom5","mom20","volume"]
    return df[cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
