# test_binance.py
from binance_api import BinanceAPI

api = BinanceAPI()
depth = api.get_order_book("USDCUSDT")
print(depth)
