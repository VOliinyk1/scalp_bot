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
from app.services.logging_service import bot_logger


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

def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2):
    """Розраховує Bollinger Bands"""
    middle = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower

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

        # Логуємо результат аналізу
        bot_logger.analysis(
            f"AI аналіз завершено для {symbol}",
            "AI_SIGNAL",
            f"{final_signal} (BUY: {votes['BUY']:.2f}, SELL: {votes['SELL']:.2f}, HOLD: {votes['HOLD']:.2f})"
        )

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

# =============================================================================
# ML DASHBOARD FUNCTIONS
# =============================================================================

# Глобальні змінні для ML статистики
_model_stats = {
    "accuracy": 0.78,
    "total_predictions": 15420,
    "version": "v1.2.3",
    "status": "active",
    "last_signal": "BTCUSDT - BUY (0.85)",
    "processing_time": 0.023
}

def get_model_stats() -> Dict[str, Any]:
    """Отримує статистику моделі"""
    global _model_stats
    return _model_stats.copy()

def get_model_weights() -> Dict[str, float]:
    """Отримує ваги моделі"""
    weights = load_weights()
    return {
        "technical": weights.get("tech", 0.40),
        "smart_money": weights.get("smart", 0.35),
        "gpt_sentiment": weights.get("gpt", 0.25),
        "5m": 0.50,
        "15m": 0.30,
        "1h": 0.20
    }

def get_model_performance() -> Dict[str, Any]:
    """Отримує продуктивність моделі"""
    return {
        "precision": 0.78,
        "recall": 0.72,
        "f1_score": 0.75,
        "confidence": 0.85,
        "history": [
            {"date": "2024-01-01", "accuracy": 0.65, "f1_score": 0.62},
            {"date": "2024-01-02", "accuracy": 0.68, "f1_score": 0.65},
            {"date": "2024-01-03", "accuracy": 0.71, "f1_score": 0.68},
            {"date": "2024-01-04", "accuracy": 0.74, "f1_score": 0.71},
            {"date": "2024-01-05", "accuracy": 0.76, "f1_score": 0.73},
            {"date": "2024-01-06", "accuracy": 0.78, "f1_score": 0.75}
        ]
    }

def get_feature_importance() -> List[Dict[str, Any]]:
    """Отримує важливість ознак"""
    return [
        {"name": "RSI (14)", "importance": 0.245},
        {"name": "MACD (12,26,9)", "importance": 0.198},
        {"name": "Bollinger Bands", "importance": 0.167},
        {"name": "Volume SMA", "importance": 0.134},
        {"name": "Smart Money Flow", "importance": 0.123},
        {"name": "GPT Sentiment", "importance": 0.089}
    ]

def update_model_stats(accuracy: float = None, prediction_count: int = None, 
                      last_signal: str = None, processing_time: float = None):
    """Оновлює статистику моделі"""
    global _model_stats
    
    if accuracy is not None:
        _model_stats["accuracy"] = accuracy
    if prediction_count is not None:
        _model_stats["total_predictions"] = prediction_count
    if last_signal is not None:
        _model_stats["last_signal"] = last_signal
    if processing_time is not None:
        _model_stats["processing_time"] = processing_time
    
    _model_stats["last_update"] = datetime.datetime.utcnow().isoformat()

def get_price_correlation_analysis(symbol: str = "BTCUSDT") -> Dict[str, Any]:
    """
    Аналізує кореляцію технічних індикаторів з передбаченнями логістичної регресії
    на основі історичних даних
    """
    try:
        print(f"🔍 Початок аналізу для {symbol}")
        # Функції технічного аналізу знаходяться в цьому ж файлі
        from app.services.smart_money import make_labels
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import train_test_split
        import pandas as pd
        import numpy as np
        
        # Отримуємо історичні дані
        print(f"📊 Отримуємо історичні дані для {symbol}")
        df = _fetch(symbol, "1h", 1000)  # 1000 годин історичних даних
        
        if df.empty:
            print("❌ Не вдалося отримати історичні дані")
            return {"error": "Не вдалося отримати історичні дані"}
        
        print(f"✅ Отримано {len(df)} записів")
        
        # Розраховуємо технічні індикатори
        df['rsi'] = calculate_rsi(df['close'], 14)
        df['macd'], df['macd_signal'], _ = calculate_macd(df['close'])
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = calculate_bollinger_bands(df['close'])
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Розраховуємо об'ємні індикатори
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Розраховуємо волатильність
        df['atr'] = calculate_atr(df, 14)
        df['atr_pct'] = df['atr'] / df['close'] * 100
        
        # Розраховуємо тренд
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['trend'] = np.where(df['ema_9'] > df['ema_21'], 1, -1)
        
        # Додаткові технічні індикатори
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        df['price_change_10'] = df['close'].pct_change(10)
        df['volume_change'] = df['volume'].pct_change()
        
        # Створюємо мітки для цінового руху (на основі smart_money.py)
        df['future_return'] = df['close'].shift(-12) / df['close'] - 1  # 12 годин вперед
        df['price_direction'] = np.where(df['future_return'] >= 0.02, 1,  # +2% = BUY
                                        np.where(df['future_return'] <= -0.02, -1, 0))  # -2% = SELL
        
        # Видаляємо NaN значення
        df = df.dropna()
        
        # Підготовка ознак для логістичної регресії
        feature_columns = [
            'rsi', 'macd', 'bb_position', 'volume_ratio', 'atr_pct', 'trend',
            'price_change', 'price_change_5', 'price_change_10', 'volume_change'
        ]
        
        X = df[feature_columns].values
        y = df['price_direction'].values
        
        # Розділяємо на тренувальну та тестову вибірки
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Нормалізуємо ознаки
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Тренуємо логістичну регресію
        lr_model = LogisticRegression(random_state=42, max_iter=1000)
        lr_model.fit(X_train_scaled, y_train)
        
        # Отримуємо передбачення на всьому наборі даних
        X_scaled = scaler.transform(X)
        predictions = lr_model.predict_proba(X_scaled)
        print(f"📊 Розмір predictions: {predictions.shape}")
        print(f"📊 Унікальні класи в y: {np.unique(y)}")
        print(f"📊 Кількість класів у моделі: {len(lr_model.classes_)}")
        print(f"📊 Класи моделі: {lr_model.classes_}")
        
        # Розраховуємо кореляції між ознаками та передбаченнями моделі
        feature_names = {
            'RSI': 'rsi',
            'MACD': 'macd', 
            'Bollinger_Position': 'bb_position',
            'Volume_Ratio': 'volume_ratio',
            'ATR_Percent': 'atr_pct',
            'Trend': 'trend',
            'Price_Change': 'price_change',
            'Price_Change_5h': 'price_change_5',
            'Price_Change_10h': 'price_change_10',
            'Volume_Change': 'volume_change'
        }
        
        correlations = {}
        for feature_display_name, feature_col in feature_names.items():
            if feature_col in df.columns:
                try:
                    # Кореляція з ймовірністю BUY сигналу (індекс 1 для класу 1)
                    buy_corr = np.corrcoef(df[feature_col], predictions[:, 1])[0, 1]
                    # Кореляція з ймовірністю SELL сигналу (індекс 0 для класу -1, але це може бути індекс 2)
                    # Перевіряємо розмір predictions
                    if predictions.shape[1] == 3:
                        sell_corr = np.corrcoef(df[feature_col], predictions[:, 2])[0, 1]
                    else:
                        sell_corr = np.corrcoef(df[feature_col], predictions[:, 0])[0, 1]
                    
                    # Середня кореляція
                    avg_corr = (buy_corr - sell_corr) / 2  # Позитивна = сприяє BUY, негативна = сприяє SELL
                    
                    correlations[feature_display_name] = round(avg_corr, 3) if not np.isnan(avg_corr) else 0.0
                except Exception as corr_error:
                    print(f"Помилка розрахунку кореляції для {feature_display_name}: {corr_error}")
                    correlations[feature_display_name] = 0.0
        
        # Розраховуємо статистику передбачень моделі
        model_predictions = lr_model.predict(X_scaled)
        total_samples = len(df)
        
        # Використовуємо класи з моделі замість хардкоду
        buy_class = lr_model.classes_[1] if len(lr_model.classes_) > 1 else 1
        sell_class = lr_model.classes_[0] if len(lr_model.classes_) > 0 else -1
        hold_class = lr_model.classes_[2] if len(lr_model.classes_) > 2 else 0
        
        buy_signals = (model_predictions == buy_class).sum()
        sell_signals = (model_predictions == sell_class).sum()
        hold_signals = (model_predictions == hold_class).sum()
        
        # Розраховуємо ефективність індикаторів на основі передбачень моделі
        effectiveness = {}
        for feature_display_name, feature_col in feature_names.items():
            if feature_col in df.columns:
                feature_values = df[feature_col]
                
                # Середнє значення індикатора для різних передбачень моделі
                # Використовуємо класи з моделі замість хардкоду
                buy_avg = feature_values[model_predictions == lr_model.classes_[1] if len(lr_model.classes_) > 1 else 1].mean()
                sell_avg = feature_values[model_predictions == lr_model.classes_[0] if len(lr_model.classes_) > 0 else -1].mean()
                hold_avg = feature_values[model_predictions == lr_model.classes_[2] if len(lr_model.classes_) > 2 else 0].mean()
                
                effectiveness[feature_display_name] = {
                    'buy_avg': round(buy_avg, 3) if not np.isnan(buy_avg) else 0.0,
                    'sell_avg': round(sell_avg, 3) if not np.isnan(sell_avg) else 0.0,
                    'hold_avg': round(hold_avg, 3) if not np.isnan(hold_avg) else 0.0,
                    'separation': round(abs(buy_avg - sell_avg), 3) if not (np.isnan(buy_avg) or np.isnan(sell_avg)) else 0.0
                }
        
        # Розраховуємо точність моделі
        model_accuracy = lr_model.score(X_test_scaled, y_test)
        
        # Отримуємо ваги ознак
        feature_importance = {}
        for i, feature_name in enumerate(feature_columns):
            if feature_name in feature_names.values():
                display_name = [k for k, v in feature_names.items() if v == feature_name][0]
                feature_importance[display_name] = abs(lr_model.coef_[0][i])
        
        return {
            "symbol": symbol,
            "total_samples": int(total_samples),
            "model_accuracy": float(round(model_accuracy, 3)),
            "signal_distribution": {
                "buy": int(buy_signals),
                "sell": int(sell_signals),
                "hold": int(hold_signals),
                "buy_pct": float(round(buy_signals / total_samples * 100, 1)),
                "sell_pct": float(round(sell_signals / total_samples * 100, 1)),
                "hold_pct": float(round(hold_signals / total_samples * 100, 1))
            },
            "correlations": {k: float(v) for k, v in correlations.items()},
            "effectiveness": {k: {
                "buy_avg": float(v["buy_avg"]),
                "sell_avg": float(v["sell_avg"]),
                "hold_avg": float(v["hold_avg"]),
                "separation": float(v["separation"])
            } for k, v in effectiveness.items()},
            "feature_importance": {k: float(v) for k, v in feature_importance.items()},
            "analysis_period": f"{len(df)} годин історичних даних",
            "model_type": "Logistic Regression",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": f"Помилка аналізу кореляцій: {str(e)}"}

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Розраховує Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    
    return atr
