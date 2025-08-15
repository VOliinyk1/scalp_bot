# app/services/trading_engine.py
"""
Торговий двигун з інтеграцією ризик-менеджменту
Автоматично виконує угоди з дотриманням правил ризик-менеджменту
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import asdict
import json

from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import Order, Trade, Signal
from app.services.binance_api import BinanceAPI
from app.services.risk_management import RiskManager, get_risk_manager
from app.services.cache import trading_cache, CACHE_TTL

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingEngine:
    """Торговий двигун"""
    
    def __init__(self):
        self.binance_api = BinanceAPI()
        self.risk_manager = get_risk_manager()
        self.is_running = False
        self.active_orders: Dict[str, Dict] = {}
        self.trading_pairs: List[str] = []
        self.account_balance = 0.0
        
    async def start(self, trading_pairs: List[str] = None):
        """
        Запускає торговий двигун
        """
        if self.is_running:
            logger.warning("Торговий двигун вже запущений")
            return
        
        self.trading_pairs = trading_pairs or ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        self.is_running = True
        
        logger.info(f"Торговий двигун запущений для пар: {self.trading_pairs}")
        
        # Запускаємо основні цикли
        await asyncio.gather(
            self._price_monitoring_loop(),
            self._signal_processing_loop(),
            self._risk_monitoring_loop(),
            self._order_management_loop()
        )
    
    async def stop(self):
        """
        Зупиняє торговий двигун
        """
        self.is_running = False
        logger.info("Торговий двигун зупинений")
    
    async def _price_monitoring_loop(self):
        """
        Цикл моніторингу цін в реальному часі
        """
        while self.is_running:
            try:
                for symbol in self.trading_pairs:
                    # Отримуємо поточну ціну
                    current_price = await self._get_current_price(symbol)
                    if current_price is None:
                        continue
                    
                    # Перевіряємо Stop Loss / Take Profit
                    exit_signals = self.risk_manager.check_stop_loss_take_profit(symbol, current_price)
                    
                    # Виконуємо сигнали виходу
                    for signal in exit_signals:
                        await self._execute_exit_signal(signal)
                    
                    # Оновлюємо кеш цін
                    trading_cache.set(
                        current_price, 
                        CACHE_TTL["orderbook"], 
                        "current_price", 
                        symbol=symbol
                    )
                
                await asyncio.sleep(5)  # Перевіряємо кожні 5 секунд
                
            except Exception as e:
                logger.error(f"Помилка в циклі моніторингу цін: {e}")
                await asyncio.sleep(10)
    
    async def _signal_processing_loop(self):
        """
        Цикл обробки торгових сигналів
        """
        while self.is_running:
            try:
                # Отримуємо останні сигнали з бази даних
                db = SessionLocal()
                try:
                    latest_signals = db.query(Signal).filter(
                        Signal.symbol.in_(self.trading_pairs),
                        Signal.created_at >= datetime.utcnow() - timedelta(minutes=5)
                    ).all()
                    
                    for signal in latest_signals:
                        if signal.final_signal in ["BUY", "SELL"]:
                            await self._process_trading_signal(signal)
                            
                finally:
                    db.close()
                
                await asyncio.sleep(30)  # Перевіряємо кожні 30 секунд
                
            except Exception as e:
                logger.error(f"Помилка в циклі обробки сигналів: {e}")
                await asyncio.sleep(60)
    
    async def _risk_monitoring_loop(self):
        """
        Цикл моніторингу ризиків
        """
        while self.is_running:
            try:
                # Отримуємо метрики ризику
                risk_metrics = self.risk_manager.get_risk_metrics()
                
                # Перевіряємо критичні рівні ризику
                if risk_metrics.total_exposure > self.risk_manager.config.max_total_exposure_usdt * 0.8:
                    logger.warning(f"Висока експозиція: {risk_metrics.total_exposure:.2f} USDT")
                
                if risk_metrics.daily_pnl < -self.risk_manager.config.max_daily_loss_usdt * 0.8:
                    logger.warning(f"Високий денний збиток: {risk_metrics.daily_pnl:.2f} USDT")
                
                # Зберігаємо метрики в кеш
                trading_cache.set(
                    asdict(risk_metrics),
                    CACHE_TTL["ai_signal"],
                    "risk_metrics"
                )
                
                await asyncio.sleep(60)  # Перевіряємо кожну хвилину
                
            except Exception as e:
                logger.error(f"Помилка в циклі моніторингу ризиків: {e}")
                await asyncio.sleep(120)
    
    async def _order_management_loop(self):
        """
        Цикл управління ордерами
        """
        while self.is_running:
            try:
                # Перевіряємо статус активних ордерів
                for order_id, order_info in list(self.active_orders.items()):
                    status = await self._check_order_status(order_info["symbol"], order_id)
                    
                    if status == "FILLED":
                        await self._handle_filled_order(order_info)
                        del self.active_orders[order_id]
                    elif status == "CANCELED":
                        del self.active_orders[order_id]
                    elif status == "EXPIRED":
                        await self._cancel_order(order_info["symbol"], order_id)
                        del self.active_orders[order_id]
                
                await asyncio.sleep(10)  # Перевіряємо кожні 10 секунд
                
            except Exception as e:
                logger.error(f"Помилка в циклі управління ордерами: {e}")
                await asyncio.sleep(30)
    
    async def _process_trading_signal(self, signal: Signal):
        """
        Обробляє торговий сигнал
        """
        try:
            symbol = signal.symbol
            side = signal.final_signal
            
            # Отримуємо поточну ціну
            current_price = await self._get_current_price(symbol)
            if current_price is None:
                return
            
            # Отримуємо баланс акаунту
            account_balance = await self._get_account_balance()
            
            # Розраховуємо розмір позиції
            quantity = self.risk_manager.calculate_position_size(
                symbol, current_price, account_balance
            )
            
            # Валідуємо угоду
            is_valid, reason = self.risk_manager.validate_trade(
                symbol, side, quantity, current_price, account_balance
            )
            
            if not is_valid:
                logger.warning(f"Угода відхилена для {symbol}: {reason}")
                return
            
            # Виконуємо угоду
            order = await self._place_order(symbol, side, quantity, current_price)
            if order:
                logger.info(f"Ордер розміщено: {symbol} {side} {quantity} @ {current_price}")
                
                # Оновлюємо позицію в менеджері ризиків
                self.risk_manager.update_position(symbol, side, quantity, current_price, order["orderId"])
                
                # Зберігаємо ордер в базі даних
                await self._save_order_to_db(order, signal)
                
        except Exception as e:
            logger.error(f"Помилка обробки сигналу для {signal.symbol}: {e}")
    
    async def _execute_exit_signal(self, signal: Dict):
        """
        Виконує сигнал виходу з позиції
        """
        try:
            symbol = signal["symbol"]
            side = signal["side"]
            quantity = signal["quantity"]
            price = signal["price"]
            reason = signal["reason"]
            
            # Розміщуємо ордер на закриття позиції
            order = await self._place_order(symbol, side, quantity, price)
            if order:
                logger.info(f"Сигнал виходу виконано: {reason} - {symbol} {side} {quantity} @ {price}")
                
                # Зберігаємо в базу даних
                await self._save_exit_order_to_db(order, reason)
            
        except Exception as e:
            logger.error(f"Помилка виконання сигналу виходу: {e}")
    
    async def _place_order(self, symbol: str, side: str, quantity: float, price: float) -> Optional[Dict]:
        """
        Розміщує ордер на біржі
        """
        try:
            # Розміщуємо лімітний ордер
            order = self.binance_api.place_limit_order(symbol, side, quantity, price)
            
            if order:
                # Додаємо до активних ордерів
                self.active_orders[order["orderId"]] = {
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "timestamp": datetime.utcnow()
                }
                
                return order
            else:
                logger.error(f"Не вдалося розмістити ордер: {symbol} {side} {quantity} @ {price}")
                return None
                
        except Exception as e:
            logger.error(f"Помилка розміщення ордера: {e}")
            return None
    
    async def _cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Скасовує ордер
        """
        try:
            result = self.binance_api.cancel_order(symbol, order_id)
            if result:
                logger.info(f"Ордер скасовано: {symbol} {order_id}")
                return True
            else:
                logger.error(f"Не вдалося скасувати ордер: {symbol} {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"Помилка скасування ордера: {e}")
            return False
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Отримує поточну ціну символу
        """
        try:
            # Перевіряємо кеш
            cached_price = trading_cache.get("current_price", symbol=symbol)
            if cached_price is not None:
                return cached_price
            
            # Отримуємо з API
            orderbook = self.binance_api.get_order_book(symbol, 1)
            if orderbook and orderbook["bids"] and orderbook["asks"]:
                bid_price = float(orderbook["bids"][0][0])
                ask_price = float(orderbook["asks"][0][0])
                current_price = (bid_price + ask_price) / 2
                
                # Кешуємо ціну
                trading_cache.set(current_price, 30, "current_price", symbol=symbol)
                
                return current_price
            
            return None
            
        except Exception as e:
            logger.error(f"Помилка отримання ціни для {symbol}: {e}")
            return None
    
    async def _get_account_balance(self) -> float:
        """
        Отримує баланс акаунту в USDT
        """
        try:
            # Тут потрібно буде інтегрувати з Binance API для отримання реального балансу
            # Поки що повертаємо фіксоване значення
            return 10000.0  # 10,000 USDT
            
        except Exception as e:
            logger.error(f"Помилка отримання балансу: {e}")
            return 0.0
    
    async def _check_order_status(self, symbol: str, order_id: str) -> str:
        """
        Перевіряє статус ордера
        """
        try:
            # Тут потрібно буде інтегрувати з Binance API для перевірки статусу
            # Поки що повертаємо базовий статус
            return "NEW"
            
        except Exception as e:
            logger.error(f"Помилка перевірки статусу ордера: {e}")
            return "UNKNOWN"
    
    async def _handle_filled_order(self, order_info: Dict):
        """
        Обробляє виконаний ордер
        """
        try:
            # Тут можна додати логіку обробки виконаних ордерів
            logger.info(f"Ордер виконано: {order_info}")
            
        except Exception as e:
            logger.error(f"Помилка обробки виконаного ордера: {e}")
    
    async def _save_order_to_db(self, order: Dict, signal: Signal):
        """
        Зберігає ордер в базу даних
        """
        try:
            db = SessionLocal()
            try:
                db_order = Order(
                    symbol=order["symbol"],
                    side=order["side"],
                    price=float(order["price"]),
                    quantity=float(order["origQty"]),
                    status=order["status"],
                    order_id=order["orderId"]
                )
                db.add(db_order)
                db.commit()
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Помилка збереження ордера в БД: {e}")
    
    async def _save_exit_order_to_db(self, order: Dict, reason: str):
        """
        Зберігає ордер виходу в базу даних
        """
        try:
            db = SessionLocal()
            try:
                db_order = Order(
                    symbol=order["symbol"],
                    side=order["side"],
                    price=float(order["price"]),
                    quantity=float(order["origQty"]),
                    status=order["status"],
                    order_id=order["orderId"]
                )
                db.add(db_order)
                db.commit()
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Помилка збереження ордера виходу в БД: {e}")

# Глобальний екземпляр торгового двигуна
trading_engine = TradingEngine()

def get_trading_engine() -> TradingEngine:
    """Отримує глобальний екземпляр торгового двигуна"""
    return trading_engine
