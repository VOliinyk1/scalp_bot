# app/main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from sqlalchemy.orm import Session

from app.ai_signals import detect_signal
from app.database import get_db
from app.models import Log, Order

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
