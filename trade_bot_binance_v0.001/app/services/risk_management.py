# app/services/risk_management.py
"""
Модуль ризик-менеджменту для торгового бота
Реалізує комплексну систему контролю ризиків в реальному часі
"""

import time
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from app.services.logging_service import bot_logger
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, Trade
from app.services.cache import trading_cache, CACHE_TTL
from app.services.binance_api import BinanceAPI

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Рівні ризику"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PositionSide(Enum):
    """Сторона позиції"""
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class RiskMetrics:
    """Метрики ризику"""
    total_exposure: float  # Загальна експозиція в USDT
    max_drawdown: float    # Максимальна просадка в %
    win_rate: float        # Відсоток прибуткових угод
    avg_win: float         # Середній прибуток
    avg_loss: float        # Середній збиток
    sharpe_ratio: float    # Коефіцієнт Шарпа
    max_position_size: float  # Максимальний розмір позиції
    daily_pnl: float       # P&L за день
    volatility: float      # Волатильність портфеля

@dataclass
class Position:
    """Позиція"""
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime

@dataclass
class RiskConfig:
    """Конфігурація ризик-менеджменту"""
    # Ліміти на позиції
    max_position_size_usdt: float = 1000.0  # Максимальний розмір позиції в USDT
    max_total_exposure_usdt: float = 5000.0  # Максимальна загальна експозиція
    max_positions_per_symbol: int = 1  # Максимум позицій на символ
    
    # Ліміти на збитки
    max_daily_loss_usdt: float = 200.0  # Максимальний денний збиток
    max_drawdown_percent: float = 10.0  # Максимальна просадка в %
    stop_loss_percent: float = 5.0  # Stop Loss в %
    take_profit_percent: float = 10.0  # Take Profit в %
    
    # Ліміти на ризик
    max_risk_per_trade_percent: float = 2.0  # Максимальний ризик на угоду в %
    max_correlation_threshold: float = 0.7  # Максимальна кореляція між активами
    
    # Часові ліміти
    max_holding_time_hours: int = 24  # Максимальний час утримання позиції
    min_time_between_trades_minutes: int = 30  # Мінімальний час між угодами
    
    # Волатильність
    max_volatility_threshold: float = 0.05  # Максимальна волатильність (5%)
    
    # Ліквідність
    min_liquidity_usdt: float = 1000000.0  # Мінімальна ліквідність в USDT (fallback)
    min_liquidity_to_position_ratio: float = 10.0  # k: вимога ліквідності як k * розмір позиції

class RiskManager:
    """Менеджер ризиків"""
    
    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
        self.binance_api = BinanceAPI()
        self.positions: Dict[str, Position] = {}
        self.risk_history: List[Dict] = []
        self.last_trade_time: Dict[str, datetime] = {}
        
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              account_balance: float) -> float:
        """
        Розраховує безпечний розмір позиції на основі ризик-менеджменту
        """
        # Базовий розмір на основі ризику на угоду
        risk_amount = account_balance * (self.config.max_risk_per_trade_percent / 100)
        
        # Враховуємо волатильність символу
        volatility = self._get_symbol_volatility(symbol)
        if volatility > self.config.max_volatility_threshold:
            risk_amount *= 0.5  # Зменшуємо розмір при високій волатильності
        
        # Враховуємо ліквідність (динамічне правило)
        liquidity = self._get_symbol_liquidity(symbol)
        # Якщо ліквідність менша за k * (плановий розмір), зменшуємо ризик
        planned_position_usdt = min(risk_amount, self.config.max_position_size_usdt)
        if liquidity < self.config.min_liquidity_to_position_ratio * planned_position_usdt:
            risk_amount *= 0.5  # пом'якшене зниження замість жорсткого блоку на етапі розміру
        
        # Розраховуємо кількість
        position_size_usdt = min(risk_amount, self.config.max_position_size_usdt)
        quantity = position_size_usdt / entry_price
        
        return quantity
    
    def validate_trade(self, symbol: str, side: str, quantity: float, 
                      price: float, account_balance: float) -> Tuple[bool, str]:
        """
        Валідує угоду на відповідність правилам ризик-менеджменту
        """
        # Перевіряємо час між угодами
        if not self._check_time_between_trades(symbol):
            return False, "Занадто часті угоди"
        
        # Перевіряємо розмір позиції
        position_value = quantity * price
        if position_value > self.config.max_position_size_usdt:
            return False, f"Розмір позиції {position_value:.2f} USDT перевищує ліміт {self.config.max_position_size_usdt} USDT"
        
        # Перевіряємо загальну експозицію
        total_exposure = self._calculate_total_exposure() + position_value
        if total_exposure > self.config.max_total_exposure_usdt:
            return False, f"Загальна експозиція {total_exposure:.2f} USDT перевищує ліміт {self.config.max_total_exposure_usdt} USDT"
        
        # Перевіряємо кількість позицій на символ
        if symbol in self.positions and len(self.positions[symbol]) >= self.config.max_positions_per_symbol:
            return False, f"Досягнуто максимум позицій для {symbol}"
        
        # Перевіряємо денний збиток
        daily_loss = self._calculate_daily_loss()
        if daily_loss < -self.config.max_daily_loss_usdt:
            return False, f"Денний збиток {daily_loss:.2f} USDT перевищує ліміт {self.config.max_daily_loss_usdt} USDT"
        
        # Перевіряємо просадку
        drawdown = self._calculate_drawdown()
        if drawdown > self.config.max_drawdown_percent:
            return False, f"Просадка {drawdown:.2f}% перевищує ліміт {self.config.max_drawdown_percent}%"
        
        # Перевіряємо волатильність
        volatility = self._get_symbol_volatility(symbol)
        if volatility > self.config.max_volatility_threshold:
            return False, f"Волатильність {volatility:.4f} перевищує ліміт {self.config.max_volatility_threshold}"
        
        # Перевіряємо ліквідність (динамічне правило): liquidity >= k * position_value
        liquidity = self._get_symbol_liquidity(symbol)
        required_liquidity = max(self.config.min_liquidity_usdt, self.config.min_liquidity_to_position_ratio * position_value)
        if liquidity < required_liquidity:
            return False, (
                f"Ліквідність {liquidity:.0f} USDT нижче необхідної {required_liquidity:.0f} USDT "
                f"(k={self.config.min_liquidity_to_position_ratio:.1f}×позиція або мінімум {self.config.min_liquidity_usdt:.0f})"
            )
        
        return True, "Угода дозволена"
    
    def update_position(self, symbol: str, side: str, quantity: float, 
                       price: float, order_id: str):
        """
        Оновлює інформацію про позицію
        """
        position_side = PositionSide.LONG if side == "BUY" else PositionSide.SHORT
        
        if symbol not in self.positions:
            self.positions[symbol] = []
        
        position = Position(
            symbol=symbol,
            side=position_side,
            quantity=quantity,
            entry_price=price,
            current_price=price,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            timestamp=datetime.utcnow()
        )
        
        self.positions[symbol].append(position)
        self.last_trade_time[symbol] = datetime.utcnow()
        
        bot_logger.trade(f"Позиція оновлена", symbol, side, price)
    
    def calculate_stop_loss_price(self, symbol: str, entry_price: float, 
                                side: str) -> float:
        """
        Розраховує ціну Stop Loss
        """
        if side == "BUY":
            return entry_price * (1 - self.config.stop_loss_percent / 100)
        else:
            return entry_price * (1 + self.config.stop_loss_percent / 100)
    
    def calculate_take_profit_price(self, symbol: str, entry_price: float, 
                                  side: str) -> float:
        """
        Розраховує ціну Take Profit
        """
        if side == "BUY":
            return entry_price * (1 + self.config.take_profit_percent / 100)
        else:
            return entry_price * (1 - self.config.take_profit_percent / 100)
    
    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> List[Dict]:
        """
        Перевіряє чи досягнуто Stop Loss або Take Profit
        """
        signals = []
        
        if symbol not in self.positions:
            return signals
        
        for position in self.positions[symbol]:
            # Оновлюємо поточну ціну
            position.current_price = current_price
            
            # Розраховуємо P&L
            if position.side == PositionSide.LONG:
                position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
            else:
                position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
            
            # Перевіряємо Stop Loss
            stop_loss_price = self.calculate_stop_loss_price(
                symbol, position.entry_price, 
                "BUY" if position.side == PositionSide.LONG else "SELL"
            )
            
            if (position.side == PositionSide.LONG and current_price <= stop_loss_price) or \
               (position.side == PositionSide.SHORT and current_price >= stop_loss_price):
                signals.append({
                    "type": "STOP_LOSS",
                    "symbol": symbol,
                    "side": "SELL" if position.side == PositionSide.LONG else "BUY",
                    "quantity": position.quantity,
                    "price": current_price,
                    "reason": f"Stop Loss досягнуто: {current_price:.8f}"
                })
            
            # Перевіряємо Take Profit
            take_profit_price = self.calculate_take_profit_price(
                symbol, position.entry_price,
                "BUY" if position.side == PositionSide.LONG else "SELL"
            )
            
            if (position.side == PositionSide.LONG and current_price >= take_profit_price) or \
               (position.side == PositionSide.SHORT and current_price <= take_profit_price):
                signals.append({
                    "type": "TAKE_PROFIT",
                    "symbol": symbol,
                    "side": "SELL" if position.side == PositionSide.LONG else "BUY",
                    "quantity": position.quantity,
                    "price": current_price,
                    "reason": f"Take Profit досягнуто: {current_price:.8f}"
                })
            
            # Перевіряємо час утримання
            holding_time = datetime.utcnow() - position.timestamp
            if holding_time.total_seconds() > self.config.max_holding_time_hours * 3600:
                signals.append({
                    "type": "TIME_EXIT",
                    "symbol": symbol,
                    "side": "SELL" if position.side == PositionSide.LONG else "BUY",
                    "quantity": position.quantity,
                    "price": current_price,
                    "reason": f"Перевищено час утримання: {holding_time.total_seconds() / 3600:.1f} годин"
                })
        
        return signals
    
    def get_risk_metrics(self) -> RiskMetrics:
        """
        Розраховує поточні метрики ризику
        """
        total_exposure = self._calculate_total_exposure()
        max_drawdown = self._calculate_drawdown()
        win_rate, avg_win, avg_loss = self._calculate_trade_stats()
        sharpe_ratio = self._calculate_sharpe_ratio()
        daily_pnl = self._calculate_daily_loss()
        volatility = self._calculate_portfolio_volatility()
        
        metrics = RiskMetrics(
            total_exposure=total_exposure,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            sharpe_ratio=sharpe_ratio,
            max_position_size=self.config.max_position_size_usdt,
            daily_pnl=daily_pnl,
            volatility=volatility
        )
        
        # Логуємо метрики ризику кожні 10 викликів
        if hasattr(self, '_metrics_log_counter'):
            self._metrics_log_counter += 1
        else:
            self._metrics_log_counter = 0
        
        if self._metrics_log_counter % 10 == 0:
            bot_logger.risk(
                f"Ризик-менеджмент: Експозиція: {total_exposure:.2f} USDT, P&L: {daily_pnl:.2f} USDT, Win Rate: {win_rate:.1%}",
                "MEDIUM",
                total_exposure
            )
        
        return metrics
    
    def _get_symbol_volatility(self, symbol: str) -> float:
        """
        Розраховує волатильність символу
        """
        cache_key = f"volatility_{symbol}"
        cached_vol = trading_cache.get(cache_key, symbol=symbol)
        if cached_vol is not None:
            return cached_vol
        
        try:
            # Отримуємо останні 100 свічок
            df = self.binance_api.get_ohlcv(symbol, "1h", 100)
            if df.empty:
                return 0.0
            
            # Розраховуємо волатильність як стандартне відхилення логарифмічних прибутків
            df['returns'] = np.log(df['close'] / df['close'].shift(1))
            volatility = df['returns'].std() * np.sqrt(24)  # Річна волатильність
            
            # Кешуємо результат
            trading_cache.set(volatility, 3600, cache_key, symbol=symbol)  # 1 година
            
            return volatility
        except Exception as e:
            logger.error(f"Помилка розрахунку волатильності для {symbol}: {e}")
            return 0.0
    
    def _get_symbol_liquidity(self, symbol: str) -> float:
        """
        Оцінює ліквідність символу
        """
        cache_key = f"liquidity_{symbol}"
        cached_liquidity = trading_cache.get(cache_key, symbol=symbol)
        if cached_liquidity is not None:
            return cached_liquidity
        
        try:
            # Отримуємо ордербук
            orderbook = self.binance_api.get_order_book(symbol, 10)
            if not orderbook:
                return 0.0
            
            # Розраховуємо ліквідність як суму топ-10 ордерів
            bids_liquidity = sum(float(bid[1]) * float(bid[0]) for bid in orderbook['bids'][:10])
            asks_liquidity = sum(float(ask[1]) * float(ask[0]) for ask in orderbook['asks'][:10])
            liquidity = min(bids_liquidity, asks_liquidity)
            
            # Кешуємо результат
            trading_cache.set(liquidity, 300, cache_key, symbol=symbol)  # 5 хвилин
            
            return liquidity
        except Exception as e:
            logger.error(f"Помилка розрахунку ліквідності для {symbol}: {e}")
            return 0.0
    
    def _check_time_between_trades(self, symbol: str) -> bool:
        """
        Перевіряє чи пройшло достатньо часу з останньої угоди
        """
        if symbol not in self.last_trade_time:
            return True
        
        time_since_last = datetime.utcnow() - self.last_trade_time[symbol]
        return time_since_last.total_seconds() >= self.config.min_time_between_trades_minutes * 60
    
    def _calculate_total_exposure(self) -> float:
        """
        Розраховує загальну експозицію
        """
        total = 0.0
        for symbol_positions in self.positions.values():
            for position in symbol_positions:
                total += position.quantity * position.current_price
        return total
    
    def _calculate_daily_loss(self) -> float:
        """
        Розраховує денний P&L
        """
        # Тут потрібно буде інтегрувати з базою даних для отримання реальних угод
        # Поки що повертаємо 0
        return 0.0
    
    def _calculate_drawdown(self) -> float:
        """
        Розраховує поточну просадку
        """
        # Тут потрібно буде інтегрувати з базою даних для розрахунку реальної просадки
        # Поки що повертаємо 0
        return 0.0
    
    def _calculate_trade_stats(self) -> Tuple[float, float, float]:
        """
        Розраховує статистику угод (win rate, середній прибуток/збиток)
        """
        # Тут потрібно буде інтегрувати з базою даних
        # Поки що повертаємо базові значення
        return 0.5, 100.0, -50.0
    
    def _calculate_sharpe_ratio(self) -> float:
        """
        Розраховує коефіцієнт Шарпа
        """
        # Тут потрібно буде інтегрувати з базою даних для розрахунку реального коефіцієнта
        # Поки що повертаємо 0
        return 0.0
    
    def _calculate_portfolio_volatility(self) -> float:
        """
        Розраховує волатильність портфеля
        """
        # Тут потрібно буде інтегрувати з базою даних
        # Поки що повертаємо 0
        return 0.0

# Глобальний екземпляр менеджера ризиків
risk_manager = RiskManager()

def get_risk_manager() -> RiskManager:
    """Отримує глобальний екземпляр менеджера ризиків"""
    return risk_manager
