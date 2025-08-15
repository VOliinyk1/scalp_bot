# app/worker.py
import time
from app.database import SessionLocal
from app.models import Signal as SignalModel
from app.services.smart_money import SmartMoneyEngine, BinanceData  # або DummyData

engine = SmartMoneyEngine(datasource=BinanceData())

def loop():
    while True:
        s = engine.latest_signal()
        with SessionLocal() as db:
            db.add(SignalModel(
                ts=s["ts"], symbol=s["symbol"], timeframe=s["timeframe"],
                signal=s["signal"], p_buy=s["p_buy"], p_sell=s["p_sell"],
                ob_imbalance=s["ob_imbalance"], top_traders_ratio=s["top_traders_ratio"]
            ))
            db.commit()
        time.sleep(60)

if __name__ == "__main__":
    loop()
