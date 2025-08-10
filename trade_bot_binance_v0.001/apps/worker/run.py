import time
from packages.smart_money.engine import SmartMoneyEngine
from packages.storage.db import SessionLocal
from packages.storage.models import Signal

engine = SmartMoneyEngine()

def loop():
    while True:
        s = engine.latest_signal()
        with SessionLocal() as db:
            db.add(Signal(
                ts=s["ts"], symbol=s["symbol"], timeframe=s["timeframe"],
                signal=s["signal"], p_buy=s["p_buy"], p_sell=s["p_sell"],
                ob_imbalance=s["ob_imbalance"], top_traders_ratio=s["top_traders_ratio"]
            ))
            db.commit()
        time.sleep(60)

if __name__ == "__main__":
    loop()
