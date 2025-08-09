# app/main.py
import threading

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.services.ai_signals import detect_signal
from app.database import get_db
from app.models import Signal
from app.telegram_bot import start_telegram_bot

app = FastAPI(title="Trade Bot")

# CORS (на випадок, якщо буде frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def main():
    return {"message": "Hello, FastAPI!"}


@app.get("/signal/{symbol}")
def get_signal(symbol: str):
    """
    Отримати торговий сигнал для символу (наприклад: BTCUSDT, ETHUSDT)
    """
    result = detect_signal(symbol.upper())
    return result

@app.get("/signals/latest/{symbol}")
def latest_signal(symbol: str, db: Session = Depends(get_db)):
    row = (db.query(Signal)
             .filter(Signal.symbol == symbol.upper())
             .order_by(Signal.id.desc())
             .first())
    if not row:
        return {"symbol": symbol.upper(), "latest": None}
    return {
        "symbol": row.symbol,
        "final_signal": row.final_signal,
        "weights": row.weights,
        "details": row.details,
        "created_at": row.created_at.isoformat()
    }

@app.on_event("startup")
def launch_telegram_bot():
    """
    Запускаємо Telegram бота в окремому потоці
    """
    threading.Thread(target=start_telegram_bot, daemon=True).start()


