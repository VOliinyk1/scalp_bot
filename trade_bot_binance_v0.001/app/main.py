# =============================================================================
# main.py
# 
# Entry point for the FastAPI application.
# Sets up API endpoints for trading signals, configures CORS, and launches
# the Telegram bot in a separate thread.
# =============================================================================

import threading

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.services.ai_signals import detect_signal
from app.database import get_db
from app.models import Signal
from app.telegram_bot import start_telegram_bot

app = FastAPI(title="Trade Bot")

# Configure CORS middleware to allow requests from any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def main():
    """
    Root endpoint.
    Returns a simple greeting message to verify the API is running.
    """
    return {"message": "Hello, FastAPI!"}

@app.get("/signal/{symbol}")
def get_signal(symbol: str):
    """
    Get trading signal for a given symbol (e.g., BTCUSDT, ETHUSDT).
    Calls the AI signal detection service and returns the result.
    """
    result = detect_signal(symbol.upper())
    return result

@app.get("/signals/latest/{symbol}")
def latest_signal(symbol: str, db: Session = Depends(get_db)):
    """
    Get the latest trading signal for a given symbol from the database.
    Returns signal details or None if no signal is found.
    """
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
    Launch the Telegram bot in a separate daemon thread when the API starts.
    """
    threading.Thread(target=start_telegram_bot, daemon=True).start()


