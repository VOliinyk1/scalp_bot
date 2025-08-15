# app/ai_signals.py
"""
AI Signal engine (enhanced):
- Multi-timeframe confirmation (5m / 15m / 1h)
- Market regime filter (ADX / ATR%)
- Normalized RSI via z-score
- Adaptive weights (configurable via ENV/JSON)
- Aggregation with Smart Money + GPT Sentiment (if available)
- Database storage for signals
Response shape (unchanged for /signal/{symbol}):
{
  "symbol": str,
  "final_signal": "BUY"|"SELL"|"HOLD"|"ERROR",
  "weights": {"BUY": float, "SELL": float, "HOLD": float},
  "details": {"tech": str, "smart_money": {...}, "gpt_sentiment": {...}, ...},
  "timestamp": iso8601
}
"""
from __future__ import annotations

import os
import json
import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from app.services.binance_api import BinanceAPI
# app/ai_signals.py (в кінці detect_signal, перед return)
from app.database import SessionLocal
from app.models import Signal


# Optional, only if you have these modules in your project
try:
    from app.services.smart_money import analyze_top_traders  # type: ignore
except Exception:
    def analyze_top_traders(symbol: str) -> dict:
        return {"symbol": symbol, "signal": "HOLD", "confidence": 0.5, "source": "SmartMoney(mock)", "timestamp": datetime.datetime.utcnow().isoformat()}

try:
    from app.services.new_sentiment import analyze_sentiment  # type: ignore
except Exception:
    def analyze_sentiment(news: List[str], symbol: str) -> dict:
        return {"signal": "HOLD", "error": "news_sentiment module unavailable"}

client = BinanceAPI()

# =========================
# Indicator calculations
# =========================

def _safe_series_last(series: pd.Series):
    s = series.dropna()
    return None if s.empty else float(s.iloc[-1])

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def rsi_zscore(prices: pd.Series, period: int = 14, z_window: int = 100) -> Tuple[float|None, float|None]:
    rsi_series = calculate_rsi(prices, period).dropna()
    if rsi_series.empty:
        return None, None
    tail = rsi_series.tail(z_window)
    mean = tail.mean()
    std = tail.std(ddof=0)
    last = float(rsi_series.iloc[-1])
    z = None if std == 0 or np.isnan(std) else float((last - mean) / std)
    return last, z

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(data: pd.Series):
    ema12 = calculate_ema(data, 12)
    ema26 = calculate_ema(data, 26)
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()  # Wilder smoothing approximation
    return atr

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = calculate_atr(df, period) * np.nan  # placeholder for index
    # recompute TR same as in ATR
    prev_close = close.shift(1)
    tr_vals = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)

    atr = tr_vals.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=close.index).ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=close.index).ewm(alpha=1/period, adjust=False).mean() / atr
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx

# =========================
# Helpers
# =========================

def _df_from_klines(klines: List[list]) -> pd.DataFrame:
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
    ])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    return df

def _fetch(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    kl = client.get_klines(symbol=symbol.upper(), interval=interval, limit=limit)
    return _df_from_klines(kl)

# =========================
# Tech signal per timeframe
# =========================

def tech_signal_for_tf(df: pd.DataFrame) -> Tuple[str, Dict[str, float|str]]:
    close = df["close"]
    volume = df["volume"]

    rsi_last, rsi_z = rsi_zscore(close, period=14, z_window=100)
    ema9 = calculate_ema(close, 9)
    ema21 = calculate_ema(close, 21)
    ema_cross_up = ema9.iloc[-1] > ema21.iloc[-1]

    macd, macd_sig, _ = calculate_macd(close)
    macd_cross_up = macd.iloc[-2] < macd_sig.iloc[-2] and macd.iloc[-1] > macd_sig.iloc[-1]
    macd_cross_down = macd.iloc[-2] > macd_sig.iloc[-2] and macd.iloc[-1] < macd_sig.iloc[-1]

    vol_spike = volume.iloc[-1] > volume.iloc[:-1].mean() * 1.5 if len(volume) > 10 else False

    # Decision using normalized RSI (z-score) + confirmations
    signal = "HOLD"
    reasons = []

    if rsi_z is not None and rsi_z <= -1.0 and ema_cross_up and macd_cross_up:
        signal = "BUY"
        reasons.append("RSI z<=-1, EMA↑, MACD↑")
    elif rsi_z is not None and rsi_z >= 1.0 and (not ema_cross_up) and macd_cross_down:
        signal = "SELL"
        reasons.append("RSI z>=+1, EMA↓, MACD↓")
    else:
        signal = "HOLD"

    details = {
        "rsi": round(rsi_last, 2) if rsi_last is not None else None,
        "rsi_z": round(rsi_z, 2) if rsi_z is not None else None,
        "ema9_gt_ema21": bool(ema_cross_up),
        "macd": round(float(macd.iloc[-1]), 6),
        "macd_signal": round(float(macd_sig.iloc[-1]), 6),
        "volume": round(float(volume.iloc[-1]), 2) if len(volume) else None,
        "vol_spike": bool(vol_spike),
        "reasons": reasons,
    }
    return signal, details

# =========================
# Regime detection
# =========================

def market_regime(df_1h: pd.DataFrame) -> Dict[str, float|str]:
    atr = calculate_atr(df_1h, period=14)
    adx = calculate_adx(df_1h, period=14)
    close = df_1h["close"].astype(float)

    atr_last = _safe_series_last(atr)
    adx_last = _safe_series_last(adx)
    close_last = float(close.iloc[-1]) if len(close) else None

    atr_pct = None
    if atr_last is not None and close_last:
        atr_pct = float(atr_last / close_last)

    # Simple regime labeling
    regime = "trend" if (adx_last is not None and adx_last >= 20) else "range"
    if atr_pct is not None and atr_pct < 0.002:  # <0.2% daily range considered very quiet
        regime = "quiet"

    return {
        "adx": round(adx_last, 2) if adx_last is not None else None,
        "atr_pct": round(atr_pct, 4) if atr_pct is not None else None,
        "label": regime,
    }

# =========================
# Adaptive weights
# =========================

def load_weights() -> Dict[str, float]:
    # env override as JSON, e.g. SIGNAL_WEIGHTS='{"tech":0.55,"smart":0.3,"gpt":0.15}'
    raw = os.getenv("SIGNAL_WEIGHTS")
    if raw:
        try:
            w = json.loads(raw)
            return {"tech": float(w.get("tech", 0.5)), "smart": float(w.get("smart", 0.25)), "gpt": float(w.get("gpt", 0.25))}
        except Exception:
            pass
    # fallback defaults
    return {"tech": 0.5, "smart": 0.25, "gpt": 0.25}

# =========================
# Main aggregation
# =========================

def detect_signal(symbol: str, techs=None) -> dict:
    try:
        # fetch data
        df_5m = _fetch(symbol, "5m", 200)
        df_15m = _fetch(symbol, "15m", 200)
        df_1h = _fetch(symbol, "1h", 500)

        # technical per timeframe
        sig_5m, det_5m = tech_signal_for_tf(df_5m)
        sig_15m, det_15m = tech_signal_for_tf(df_15m)
        sig_1h, det_1h = tech_signal_for_tf(df_1h)

        # market regime from 1h
        regime = market_regime(df_1h)

        # Multi-timeframe rule (conservative):
        # BUY if 5m=BUY and 15m!=SELL and 1h!=SELL; SELL symmetrical
        tech_signal = "HOLD"
        if sig_5m == "BUY" and sig_15m != "SELL" and sig_1h != "SELL":
            tech_signal = "BUY"
        elif sig_5m == "SELL" and sig_15m != "BUY" and sig_1h != "BUY":
            tech_signal = "SELL"
        else:
            tech_signal = "HOLD"

        # Adjust tech signal in very quiet regime
        if regime.get("label") == "quiet":
            # prefer HOLD in ultra-low volatility to reduce noise
            tech_signal = "HOLD"

        # External signals
        techs = {
            'rsi': det_1h.get("rsi"),
            'rsi_z': det_1h.get("rsi_z"),
            'ema9_gt_ema21': det_1h.get("ema9_gt_ema21"),
            'macd': det_1h.get("macd"),
            'macd_signal': det_1h.get("macd_signal"),
            'volume': det_1h.get("volume"),
            'vol_spike': det_1h.get("vol_spike"),
            'reasons': det_1h.get("reasons", []),
            'regime': regime.get("label"),
            'atr_pct': regime.get("atr_pct"),
            'adx': regime.get("adx")
        }
        smart = analyze_top_traders(symbol)
        gpt = analyze_sentiment([], symbol=symbol, techs=techs)

        # Adaptive weights
        w = load_weights()
        votes = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}

        votes[tech_signal] += w["tech"]
        votes[smart.get("signal", "HOLD")] += w["smart"]
        votes[gpt.get("signal", "HOLD")] += w["gpt"]

        final_signal = max(votes, key=votes.get)

        details = {
            "tech": tech_signal,
            "tf": {
                "5m": {"signal": sig_5m, **det_5m},
                "15m": {"signal": sig_15m, **det_15m},
                "1h": {"signal": sig_1h, **det_1h},
            },
            "regime": regime,
            "smart_money": smart,
            "gpt_sentiment": gpt,
        }
        
        db = SessionLocal()
        try:
            db.add(Signal(
                symbol=symbol,
                final_signal=final_signal,
                weights={"BUY": round(votes["BUY"],2), "SELL": round(votes["SELL"],2), "HOLD": round(votes["HOLD"],2)},
                details=details
            ))
            db.commit()
        finally:
            db.close()
        
        return {
            "symbol": symbol,
            "final_signal": final_signal,
            "weights": {"BUY": round(votes["BUY"], 2), "SELL": round(votes["SELL"], 2), "HOLD": round(votes["HOLD"], 2)},
            "details": details,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {"symbol": symbol, "final_signal": "ERROR", "error": str(e), "techs": techs or {}}
