# app/bot.py

import threading
import time
from .binance_api import BinanceAPI
from .database import SessionLocal
from .models import Order, Log, Base
from sqlalchemy.exc import SQLAlchemyError
from .binance_api import client  # клієнт Binance API
from .database import get_db
from sqlalchemy.orm import Session
import asyncio
import datetime

class ScalpingBot:
    def __init__(self, symbol="USDCUSDT", spread=0.0001, quantity=100.0, interval=5):
        self.symbol = symbol
        self.spread = spread  # мінімальний спред для прибутку
        self.quantity = quantity  # обсяг торгів
        self.interval = interval  # скільки секунд чекати між ітераціями
        self.api = BinanceAPI()
        self.running = False
        self.thread = None
        self.buy_order_id = None
        self.sell_order_id = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def run(self):
        while self.running:
            try:
                depth = self.api.get_order_book(self.symbol, limit=5)
                if not depth:
                    time.sleep(self.interval)
                    continue

                best_bid = float(depth["bids"][0][0])
                best_ask = float(depth["asks"][0][0])

                buy_price = round(best_bid - self.spread, 5)
                sell_price = round(best_ask + self.spread, 5)

                # Скасування попередніх ордерів (якщо є)
                if self.buy_order_id:
                    self.api.cancel_order(self.symbol, self.buy_order_id)
                if self.sell_order_id:
                    self.api.cancel_order(self.symbol, self.sell_order_id)

                # Виставлення нових ордерів
                buy_order = self.api.place_limit_order(
                    symbol=self.symbol,
                    side="BUY",
                    quantity=self.quantity,
                    price=buy_price
                )
                sell_order = self.api.place_limit_order(
                    symbol=self.symbol,
                    side="SELL",
                    quantity=self.quantity,
                    price=sell_price
                )

                self.buy_order_id = buy_order["orderId"] if buy_order else None
                self.sell_order_id = sell_order["orderId"] if sell_order else None

                # Зберігаємо ордери в БД
                self.log_order("BUY", buy_price, self.buy_order_id)
                self.log_order("SELL", sell_price, self.sell_order_id)

                time.sleep(self.interval)

            except Exception as e:
                self.log_event("ERROR", f"Exception: {str(e)}")
                time.sleep(self.interval)

    def log_order(self, side, price, order_id):
        db = SessionLocal()
        try:
            order = Order(
                symbol=self.symbol,
                side=side,
                price=price,
                quantity=self.quantity,
                status="NEW",
                order_id=str(order_id)
            )
            db.add(order)
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            print("DB error:", e)
        finally:
            db.close()

    def log_event(self, level, message):
        db = SessionLocal()
        try:
            log = Log(level=level, message=message)
            db.add(log)
            db.commit()
        except:
            db.rollback()
        finally:
            db.close()


class SimulatedScalpingBot:
    def __init__(self, symbol: str, test_balance: float = 10000.0):
        self.symbol = symbol
        self.running = False
        self.test_balance = test_balance
        self.open_orders = []

    def get_best_prices(self):
        try:
            order_book = client.get_order_book(symbol=self.symbol, limit=5)
            best_bid = float(order_book['bids'][0][0])
            best_ask = float(order_book['asks'][0][0])
            return best_bid, best_ask
        except Exception as e:
            print(f"[ERROR] get_best_prices: {e}")
            return None, None

    async def main_loop(self, db: Session):
        print(f"[INFO] Simulated Bot started on {self.symbol}")
        while self.active:
            bid, ask = self.get_best_prices()
            if not bid or not ask:
                await asyncio.sleep(1)
                continue

            buy_price = round(bid - 0.0001, 5)
            sell_price = round(ask + 0.0001, 5)

            quantity = round(10 / buy_price, 5)  # купити на 10$

            if self.test_balance >= buy_price * quantity:
                self.test_balance -= buy_price * quantity
                self.open_orders.append({
                    "side": "buy",
                    "price": buy_price,
                    "quantity": quantity,
                    "time": datetime.datetime.utcnow()
                })

                # логування в БД
                order = Log(
                    level="INFO",
                    message=f"Simulated BUY: {quantity} {self.symbol} @ {buy_price}"
                )
                db.add(order)
                db.commit()

                print(f"[SIM BUY] {quantity} {self.symbol} @ {buy_price}")

            # умовна реалізація продажу (кожен другий цикл)
            if self.open_orders:
                open_buy = self.open_orders.pop(0)
                sell_price_exec = round(open_buy["price"] + 0.001, 5)Ы
                self.test_balance += sell_price_exec * open_buy["quantity"]

                order = Order(
                    symbol=self.symbol,
                    side="SELL",
                    price=sell_price_exec,
                    quantity=open_buy["quantity"],
                    status="FILLED",
                    order_id=f"simulated_{datetime.datetime.utcnow().isoformat()}"
                )
                db.add(order)
                db.commit()

                print(f"[SIM SELL] {open_buy['quantity']} {self.symbol} @ {sell_price_exec}")

            await asyncio.sleep(5)

    async def start(self, db: Session):
        self.active = True
        await asyncio.create_task(self.main_loop(db))

    def stop(self):
        self.active = False
