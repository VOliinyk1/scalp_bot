import pandas as pd

def make_labels(df: pd.DataFrame, horizon_bars: int = 12, pos_th=0.002, neg_th=-0.002) -> pd.Series:
    future = df["close"].shift(-horizon_bars)
    ret = (future / df["close"] - 1.0)
    y = (ret >= pos_th).astype(int) - (ret <= neg_th).astype(int)
    return y.fillna(0)
