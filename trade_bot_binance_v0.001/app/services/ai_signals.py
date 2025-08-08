import pandas as pd
import datetime

from app.services.smart_money import analyze_top_traders
from app.services.new_sentiment import analyze_sentiment
from app.services.binance_api import BinanceAPI

client = BinanceAPI()

# === Технічні індикатори ===
def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).iloc[-1]

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(data: pd.Series):
    ema12 = calculate_ema(data, 12)
    ema26 = calculate_ema(data, 26)
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

# === Основна логіка обʼєднання сигналів ===
def detect_signal(symbol: str) -> dict:
    try:
        # Отримуємо свічки
        klines = client.get_klines(symbol=symbol.upper(), interval='5m', limit=100)
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
        ])
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        close_prices = df["close"]
        volumes = df["volume"]

        # === Індикатори ===
        rsi = calculate_rsi(close_prices)
        ema_short = calculate_ema(close_prices, 9)
        ema_long = calculate_ema(close_prices, 21)
        last_cross = ema_short.iloc[-1] > ema_long.iloc[-1]
        volume_spike = volumes.iloc[-1] > volumes[:-1].mean() * 1.5
        macd_line, signal_line, _ = calculate_macd(close_prices)
        macd_cross_up = macd_line.iloc[-2] < signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]
        macd_cross_down = macd_line.iloc[-2] > signal_line.iloc[-2] and macd_line.iloc[-1] < signal_line.iloc[-1]

        # === Технічний сигнал ===
        tech_signal = "HOLD"
        reasons = []
        if rsi < 30 and last_cross and volume_spike and macd_cross_up:
            tech_signal = "BUY"
            reasons.append("RSI < 30, EMA ↑, Volume spike, MACD ↑")
        elif rsi > 70 and not last_cross and macd_cross_down:
            tech_signal = "SELL"
            reasons.append("RSI > 70, EMA ↓, MACD ↓")

        # === Smart Money сигнал ===
        smart = analyze_top_traders(symbol)

        # === GPT-сентимент ===
        techs = {
            "rsi": rsi,
            "ema_short": ema_short.iloc[-1],
            "ema_long": ema_long.iloc[-1],
            "macd": macd_line.iloc[-1],
            "macd_signal": signal_line.iloc[-1],
            "volume_spike": volume_spike,
            "reasons": reasons
        }
        print(f"Techs for {symbol}: {techs}")
        news = analyze_sentiment([], symbol=symbol, techs=techs)  # в майбутньому передати новини сюди

        # === Аггрегація ===
        votes = {"BUY": 0, "SELL": 0, "HOLD": 0}
        weights = {"tech": 0.5, "smart": 0.25, "gpt": 0.25}

        votes[tech_signal] += weights["tech"]
        votes[smart["signal"]] += weights["smart"]
        votes[news["signal"]] += weights["gpt"]

        final_signal = max(votes, key=votes.get)

        return {
            "symbol": symbol,
            "final_signal": final_signal,
            "weights": votes,
            "details": {
                "tech": tech_signal,
                "smart_money": smart,
                "gpt_sentiment": news
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

    except Exception as e:
        return {
            "symbol": symbol,
            "final_signal": "ERROR",
            "error": str(e)
        }
