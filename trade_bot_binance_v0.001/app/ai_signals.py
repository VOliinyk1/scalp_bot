import pandas as pd
import numpy as np
import datetime
from binance_api import get_klines

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))[-1]

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(data: pd.Series):
    ema12 = calculate_ema(data, 12)
    ema26 = calculate_ema(data, 26)
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def detect_signal(symbol: str, interval: str = "5m", limit: int = 100) -> dict:
    try:
        klines = get_klines(symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
        ])
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        close_prices = df["close"]
        volumes = df["volume"]

        # Індикатори
        rsi = calculate_rsi(close_prices)
        ema_short = calculate_ema(close_prices, 9)
        ema_long = calculate_ema(close_prices, 21)
        last_cross = ema_short.iloc[-1] > ema_long.iloc[-1]
        volume_spike = volumes.iloc[-1] > volumes[:-1].mean() * 1.5

        macd_line, signal_line, histogram = calculate_macd(close_prices)
        macd_cross_up = macd_line.iloc[-2] < signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]
        macd_cross_down = macd_line.iloc[-2] > signal_line.iloc[-2] and macd_line.iloc[-1] < signal_line.iloc[-1]

        # Логіка сигналів
        signal = "HOLD"
        reasons = []

        if rsi < 30 and last_cross and volume_spike and macd_cross_up:
            signal = "BUY"
            reasons = ["RSI < 30", "EMA crossover ↑", "Volume spike", "MACD crossover ↑"]
        elif rsi > 70 and not last_cross and macd_cross_down:
            signal = "SELL"
            reasons = ["RSI > 70", "EMA crossover ↓", "MACD crossover ↓"]

        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": 0.9 if signal != "HOLD" else 0.5,
            "reasons": reasons,
            "rsi": round(rsi, 2),
            "macd": round(macd_line.iloc[-1], 5),
            "macd_signal": round(signal_line.iloc[-1], 5),
            "volume": round(volumes.iloc[-1], 2),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "symbol": symbol,
            "signal": "ERROR",
            "error": str(e)
        }
