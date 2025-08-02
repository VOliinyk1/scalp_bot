# app/main.py

from fastapi import FastAPI
from app.bot import ScalpingBot, SimulatedScalpingBot
from app.database import get_db
from app.models import Log, Order
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db


app = FastAPI(title="Stablecoin Scalping Bot")

# CORS (на випадок, якщо буде frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = ScalpingBot()
test_bot = SimulatedScalpingBot(symbol="USDCUSDT") 

@app.get("/start")
def start_bot():
    if not bot.running:
        bot.start()
        return {"status": "✅ Бот запущено"}
    return {"status": "⚠️ Бот уже працює"}

@app.get("/start_simulated")
async def start_simulated_bot(db: Session = Depends(get_db)):
    if not test_bot.running:
        await test_bot.start(db)
        return {"status": "✅Симульований Бот запущено"}
    return {"status": "⚠️ Симульований Бот уже працює"}

@app.get("/stop")
def stop_bot():
    if bot.running:
        bot.stop()
        return {"status": "🛑 Бот зупинено"}
    return {"status": "⚠️ Бот вже зупинений"}

@app.get("/status")
def bot_status():
    return {"running": bot.running}

@app.get("/logs")
def get_logs(db: Session = Depends(get_db)):
    logs = db.query(Log).order_by(Log.timestamp.desc()).limit(20).all()
    return [
        {"timestamp": l.timestamp, "level": l.level, "message": l.message}
        for l in logs
    ]

@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(20).all()
    return [
        {
            "timestamp": o.created_at,
            "symbol": o.symbol,
            "side": o.side,
            "price": o.price,
            "quantity": o.quantity,
            "status": o.status,
            "order_id": o.order_id
        }
        for o in orders
    ]