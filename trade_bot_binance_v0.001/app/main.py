# app/main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from sqlalchemy.orm import Session
import threading

from app.ai_signals import detect_signal
from app.database import get_db
from app.models import Log, Order
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

@app.on_event("startup")
def launch_telegram_bot():
    """
    Запускаємо Telegram бота в окремому потоці
    """
    threading.Thread(target=start_telegram_bot, daemon=True).start()
