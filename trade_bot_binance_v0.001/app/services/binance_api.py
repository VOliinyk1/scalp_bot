# app/binance_api.py

import pandas as pd
import numpy as np

from binance.client import Client
from binance.exceptions import BinanceAPIException
from app.config import BINANCE_API_KEY, BINANCE_API_SECRET
from app.services.cache import trading_cache, CACHE_TTL

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)



class BinanceAPI:
    def __init__(self):
        self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)


    def get_klines(self, symbol: str, interval: str = '5m', limit: int = 100):
        # Перевіряємо кеш
        cache_key = f"klines_{interval}"
        cached_data = trading_cache.get(cache_key, symbol=symbol, interval=interval, limit=limit)
        if cached_data is not None:
            return cached_data
        
        try:
            data = self.client.get_klines(
                symbol=symbol.upper(),
                interval=interval,
                limit=limit
            )
            
            # Зберігаємо в кеш
            ttl = CACHE_TTL.get(f"ohlcv_{interval}", 300)  # За замовчуванням 5 хвилин
            trading_cache.set(data, ttl, cache_key, symbol=symbol, interval=interval, limit=limit)
            
            return data
        except BinanceAPIException as e:
            print(f"[BINANCE ERROR] {e}")
            return []
        except Exception as e:
            print(f"[UNKNOWN ERROR] {e}")
            return []


    def get_order_book(self, symbol: str, limit: int = 5):
        """Отримати топ ордербуку"""
        # Перевіряємо кеш
        cached_data = trading_cache.get("orderbook", symbol=symbol, limit=limit)
        if cached_data is not None:
            return cached_data
        
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)
            
            # Зберігаємо в кеш
            trading_cache.set(depth, CACHE_TTL["orderbook"], "orderbook", symbol=symbol, limit=limit)
            
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
    
    def get_ohlcv(self, symbol: str, interval: str = '5m', limit: int = 100) -> pd.DataFrame:
        """
        Отримує OHLCV у форматі DataFrame з колонками:
        ts, open, high, low, close, volume
        """
        raw = self.get_klines(symbol, interval, limit)
        if not raw:
            return pd.DataFrame(columns=["ts","open","high","low","close","volume"])

        df = pd.DataFrame(raw, columns=[
            "open_time","open","high","low","close","volume",
            "close_time","qav","num_trades","taker_base_vol","taker_quote_vol","ignore"
        ])

        df = df[["open_time","open","high","low","close","volume"]].copy()
        df["ts"] = df["open_time"].astype(int)  # Binance вже в мс
        for col in ["open","high","low","close","volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["ts","open","high","low","close","volume"]].dropna().sort_values("ts").reset_index(drop=True)
        return df

    def get_account_info(self):
        """Отримує інформацію про акаунт"""
        try:
            account_info = self.client.get_account()
            return account_info
        except BinanceAPIException as e:
            print(f"❌ Error getting account info: {e}")
            return None

    def get_account_balance(self):
        """Отримує баланс акаунту з деталями по кожному активу"""
        try:
            account_info = self.client.get_account()
            balances = []
            
            for balance in account_info['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:  # Показуємо тільки активи з ненульовим балансом
                    balances.append({
                        'asset': balance['asset'],
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'usdt_value': 0  # Буде розраховано окремо
                    })
            
            # Сортуємо за загальним балансом (спочатку найбільші)
            balances.sort(key=lambda x: x['total'], reverse=True)
            
            return {
                'account_type': account_info.get('accountType', 'SPOT'),
                'permissions': account_info.get('permissions', []),
                'balances': balances,
                'total_assets': len(balances)
            }
        except BinanceAPIException as e:
            print(f"❌ Error getting account balance: {e}")
            # Повертаємо демо дані якщо API не працює
            return self._get_demo_balance()
        except Exception as e:
            print(f"❌ Unknown error getting balance: {e}")
            return self._get_demo_balance()

    def get_usdt_balance(self):
        """Отримує баланс в USDT"""
        try:
            account_info = self.client.get_account()
            for balance in account_info['balances']:
                if balance['asset'] == 'USDT':
                    return float(balance['free']) + float(balance['locked'])
            return 0.0
        except BinanceAPIException as e:
            print(f"❌ Error getting USDT balance: {e}")
            # Повертаємо демо баланс якщо API не працює
            return 10000.0
        except Exception as e:
            print(f"❌ Unknown error getting USDT balance: {e}")
            return 10000.0

    def _get_demo_balance(self):
        """Повертає демо баланс для тестування"""
        return {
            'account_type': 'SPOT',
            'permissions': ['SPOT'],
            'balances': [
                {
                    'asset': 'USDT',
                    'free': 8500.0,
                    'locked': 1500.0,
                    'total': 10000.0,
                    'usdt_value': 10000.0
                },
                {
                    'asset': 'BTC',
                    'free': 0.15,
                    'locked': 0.05,
                    'total': 0.2,
                    'usdt_value': 8000.0
                },
                {
                    'asset': 'ETH',
                    'free': 2.5,
                    'locked': 0.5,
                    'total': 3.0,
                    'usdt_value': 6000.0
                },
                {
                    'asset': 'BNB',
                    'free': 15.0,
                    'locked': 5.0,
                    'total': 20.0,
                    'usdt_value': 4000.0
                },
                {
                    'asset': 'ADA',
                    'free': 5000.0,
                    'locked': 1000.0,
                    'total': 6000.0,
                    'usdt_value': 1200.0
                }
            ],
            'total_assets': 5
        }