import random
import datetime

# Мокові топ трейдери Binance (імітація через API або парсинг у майбутньому)
TOP_TRADERS = [
    {"name": "AlphaWhale", "position": "LONG", "symbol": "ETHUSDT", "confidence": 0.85},
    {"name": "BetaSniper", "position": "SHORT", "symbol": "BTCUSDT", "confidence": 0.75},
    {"name": "GammaPro", "position": "LONG", "symbol": "ETHUSDT", "confidence": 0.82},
]

def analyze_top_traders(symbol: str) -> dict:
    """
    Повертає агрегований сигнал з боку топ-трейдерів
    """
    filtered = [t for t in TOP_TRADERS if t["symbol"] == symbol.upper()]

    long_count = sum(1 for t in filtered if t["position"] == "LONG")
    short_count = sum(1 for t in filtered if t["position"] == "SHORT")

    signal = "NEUTRAL"
    if long_count > short_count:
        signal = "BUY"
    elif short_count > long_count:
        signal = "SELL"

    return {
        "symbol": symbol,
        "signal": signal,
        "confidence": round((max(long_count, short_count) / len(filtered)) if filtered else 0.5, 2),
        "source": "SmartMoney",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
