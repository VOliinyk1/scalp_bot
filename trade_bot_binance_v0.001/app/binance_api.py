# app/binance_api.py

from binance.client import Client
from binance.exceptions import BinanceAPIException
from .config import BINANCE_API_KEY, BINANCE_API_SECRET

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

class BinanceAPI:
    def __init__(self):
        self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)


    def get_klines(symbol: str, interval: str, limit: int):
        try:
            return client.get_klines(symbol=symbol.upper(), interval=interval, limit=limit)
        except BinanceAPIException as e:
            print(f"[BINANCE ERROR] {e}")
            return []
        except Exception as e:
            print(f"[UNKNOWN ERROR] {e}")
            return []


    def get_order_book(self, symbol: str, limit: int = 5):
        """Отримати топ ордербуку"""
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)
            return depth
        except BinanceAPIException as e:
            print(f"❌ Error getting order book: {e}")
            return None

    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float):
        """Виставити лімітний ордер (BUY/SELL)"""
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                price=str(price)
            )
            return order
        except BinanceAPIException as e:
            print(f"❌ Error placing order: {e}")
            return None

    def cancel_order(self, symbol: str, order_id: str):
        """Скасувати ордер за ID"""
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            return result
        except BinanceAPIException as e:
            print(f"❌ Error cancelling order: {e}")
            return None
