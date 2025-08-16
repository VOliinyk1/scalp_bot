# app/binance_api.py

import pandas as pd
import numpy as np
import datetime

from binance.client import Client
from binance.exceptions import BinanceAPIException
from app.config import BINANCE_API_KEY, BINANCE_API_SECRET
from app.services.cache import trading_cache, CACHE_TTL
from decimal import Decimal, ROUND_DOWN, ROUND_UP

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)



class BinanceAPI:
    def __init__(self):
        self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

    # ----------------------
    # Helpers for filters
    # ----------------------
    def _get_symbol_info(self, symbol: str) -> dict | None:
        cache_key = "symbol_info"
        cached = trading_cache.get(cache_key, symbol=symbol)
        if cached is not None:
            return cached
        try:
            info = self.client.get_symbol_info(symbol)
            if info:
                trading_cache.set(info, 3600, cache_key, symbol=symbol)
            return info
        except Exception:
            return None

    def _apply_filters(self, symbol: str, quantity: float, price: float) -> tuple[str, str]:
        info = self._get_symbol_info(symbol)
        if not info:
            # Fallback: return original values as strings
            return str(quantity), str(price)

        step_size = None
        min_qty = None
        tick_size = None
        min_price = None
        min_notional = None

        for f in info.get("filters", []):
            ftype = f.get("filterType")
            if ftype == "LOT_SIZE":
                step_size = f.get("stepSize")
                min_qty = f.get("minQty")
            elif ftype == "PRICE_FILTER":
                tick_size = f.get("tickSize")
                min_price = f.get("minPrice")
            elif ftype == "MIN_NOTIONAL":
                min_notional = f.get("minNotional")

        q = Decimal(str(quantity))
        p = Decimal(str(price))

        def round_to_step(value: Decimal, step: str, rounding=ROUND_DOWN) -> Decimal:
            step_dec = Decimal(str(step))
            if step_dec <= 0:
                return value
            n = (value / step_dec).to_integral_value(rounding=rounding)
            return n * step_dec

        if tick_size:
            p = round_to_step(p, tick_size, rounding=ROUND_DOWN)
        if min_price:
            min_p = Decimal(str(min_price))
            if p < min_p:
                p = min_p

        if step_size:
            q = round_to_step(q, step_size, rounding=ROUND_DOWN)
        if min_qty:
            min_q = Decimal(str(min_qty))
            if q < min_q:
                q = min_q

        if min_notional:
            mn = Decimal(str(min_notional))
            if p * q < mn and p > 0:
                # increase quantity to satisfy notional, then round UP to step
                req_q = (mn / p)
                if step_size:
                    q = round_to_step(req_q, step_size, rounding=ROUND_UP)
                else:
                    q = req_q

        # Ensure non-zero positive
        if q <= 0:
            if min_qty:
                q = Decimal(str(min_qty))
            else:
                q = Decimal("0.00000001")

        q_str = format(q, 'f')
        p_str = format(p, 'f')
        # Avoid scientific notation and ensure no trailing zeros beyond step; Binance accepts trimmed
        if '.' in q_str:
            q_str = q_str.rstrip('0').rstrip('.')
        if '.' in p_str:
            p_str = p_str.rstrip('0').rstrip('.')
        return q_str, p_str


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
            adj_qty, adj_price = self._apply_filters(symbol, quantity, price)
            # Debug: print adjusted params
            print(f"🔧 Placing order adjusted: {symbol} {side} qty={adj_qty} price={adj_price}")
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=adj_qty,
                price=str(adj_price)
            )
            return order
        except BinanceAPIException as e:
            try:
                info = self._get_symbol_info(symbol)
                print(f"❌ Error placing order: {e}. Filters: {info.get('filters') if info else 'N/A'}")
            except Exception:
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
        """Отримує детальну інформацію про акаунт"""
        try:
            account_info = self.client.get_account()
            
            # Отримуємо баланс для розрахунку загальної вартості
            balance_info = self.get_account_balance()
            total_value = balance_info.get('total_portfolio_value', 0) if balance_info else 0
            
            return {
                'account_type': account_info.get('accountType', 'SPOT'),
                'permissions': account_info.get('permissions', []),
                'maker_commission': account_info.get('makerCommission', 0),
                'taker_commission': account_info.get('takerCommission', 0),
                'buyer_commission': account_info.get('buyerCommission', 0),
                'seller_commission': account_info.get('sellerCommission', 0),
                'can_trade': account_info.get('canTrade', False),
                'can_withdraw': account_info.get('canWithdraw', False),
                'can_deposit': account_info.get('canDeposit', False),
                'update_time': account_info.get('updateTime', 0),
                'total_portfolio_value': total_value,
                'timestamp': self.client.get_server_time()['serverTime']
            }
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
            
            # Розраховуємо USDT вартість для кожного активу
            balances = self._calculate_usdt_values(balances)
            
            # Сортуємо за USDT вартістю (спочатку найбільші)
            balances.sort(key=lambda x: x['usdt_value'], reverse=True)
            
            # Розраховуємо загальну вартість портфеля
            total_portfolio_value = sum(balance['usdt_value'] for balance in balances)
            
            return {
                'account_type': account_info.get('accountType', 'SPOT'),
                'permissions': account_info.get('permissions', []),
                'balances': balances,
                'total_assets': len(balances),
                'total_portfolio_value': total_portfolio_value,
                'timestamp': self.client.get_server_time()['serverTime']
            }
        except BinanceAPIException as e:
            print(f"❌ Error getting account balance: {e}")
            # Повертаємо демо дані якщо API не працює
            return self._get_demo_balance()
        except Exception as e:
            print(f"❌ Unknown error getting balance: {e}")
            return self._get_demo_balance()

    def _calculate_usdt_values(self, balances):
        """Розраховує USDT вартість для кожного активу"""
        try:
            # Отримуємо ціни всіх пар з USDT
            ticker_prices = self.client.get_all_tickers()
            price_dict = {ticker['symbol']: float(ticker['price']) for ticker in ticker_prices}
            
            for balance in balances:
                asset = balance['asset']
                
                if asset == 'USDT':
                    balance['usdt_value'] = balance['total']
                    balance['price_usdt'] = 1.0
                else:
                    # Шукаємо пару з USDT
                    symbol = f"{asset}USDT"
                    if symbol in price_dict:
                        price = price_dict[symbol]
                        balance['usdt_value'] = balance['total'] * price
                        balance['price_usdt'] = price
                    else:
                        # Якщо немає прямої пари з USDT, шукаємо через BTC
                        btc_symbol = f"{asset}BTC"
                        if btc_symbol in price_dict and 'BTCUSDT' in price_dict:
                            btc_price = price_dict[btc_symbol]
                            btc_usdt_price = price_dict['BTCUSDT']
                            price = btc_price * btc_usdt_price
                            balance['usdt_value'] = balance['total'] * price
                            balance['price_usdt'] = price
                        else:
                            balance['usdt_value'] = 0
                            balance['price_usdt'] = 0
            
            return balances
        except Exception as e:
            print(f"❌ Error calculating USDT values: {e}")
            # Якщо не можемо отримати ціни, повертаємо без USDT вартості
            for balance in balances:
                if balance['asset'] == 'USDT':
                    balance['usdt_value'] = balance['total']
                    balance['price_usdt'] = 1.0
                else:
                    balance['usdt_value'] = 0
                    balance['price_usdt'] = 0
            return balances

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

    def get_current_price(self, symbol: str) -> float:
        """Отримує поточну ціну для символу"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            print(f"❌ Error getting price for {symbol}: {e}")
            return 0.0
        except Exception as e:
            print(f"❌ Unknown error getting price for {symbol}: {e}")
            return 0.0

    def get_portfolio_summary(self):
        """Отримує короткий звіт про портфель"""
        try:
            balance_info = self.get_account_balance()
            if not balance_info:
                return None
            
            # Розраховуємо статистику
            total_value = balance_info.get('total_portfolio_value', 0)
            usdt_balance = 0
            crypto_value = 0
            
            for balance in balance_info.get('balances', []):
                if balance['asset'] == 'USDT':
                    usdt_balance = balance['usdt_value']
                else:
                    crypto_value += balance['usdt_value']
            
            return {
                'total_value': total_value,
                'usdt_balance': usdt_balance,
                'crypto_value': crypto_value,
                'assets_count': balance_info.get('total_assets', 0),
                'timestamp': balance_info.get('timestamp', 0)
            }
        except Exception as e:
            print(f"❌ Error getting portfolio summary: {e}")
            return None

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
                    'usdt_value': 10000.0,
                    'price_usdt': 1.0
                },
                {
                    'asset': 'BTC',
                    'free': 0.15,
                    'locked': 0.05,
                    'total': 0.2,
                    'usdt_value': 8000.0,
                    'price_usdt': 40000.0
                },
                {
                    'asset': 'ETH',
                    'free': 2.5,
                    'locked': 0.5,
                    'total': 3.0,
                    'usdt_value': 6000.0,
                    'price_usdt': 2000.0
                },
                {
                    'asset': 'BNB',
                    'free': 15.0,
                    'locked': 5.0,
                    'total': 20.0,
                    'usdt_value': 4000.0,
                    'price_usdt': 200.0
                },
                {
                    'asset': 'ADA',
                    'free': 5000.0,
                    'locked': 1000.0,
                    'total': 6000.0,
                    'usdt_value': 1200.0,
                    'price_usdt': 0.2
                }
            ],
            'total_assets': 5,
            'total_portfolio_value': 29200.0,
            'timestamp': int(datetime.datetime.now().timestamp() * 1000)
        }