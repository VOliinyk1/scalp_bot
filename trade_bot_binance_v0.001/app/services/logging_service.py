# app/services/logging_service.py
"""
Сервіс логування для торгового бота
Зберігає та надає доступ до логів роботи бота
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import deque
import threading

# Глобальний буфер для логів
bot_logs = deque(maxlen=1000)  # Зберігаємо останні 1000 логів
log_lock = threading.Lock()

class BotLogger:
    """Логер для торгового бота"""
    
    def __init__(self, name: str = "TradingBot"):
        self.name = name
        self.logger = logging.getLogger(name)
        
    def info(self, message: str, category: str = "INFO"):
        """Логує інформаційне повідомлення"""
        self._log("INFO", message, category)
        
    def warning(self, message: str, category: str = "WARNING"):
        """Логує попередження"""
        self._log("WARNING", message, category)
        
    def error(self, message: str, category: str = "ERROR"):
        """Логує помилку"""
        self._log("ERROR", message, category)
        
    def success(self, message: str, category: str = "SUCCESS"):
        """Логує успішну дію"""
        self._log("SUCCESS", message, category)
        
    def trade(self, message: str, symbol: str = None, side: str = None, price: float = None):
        """Логує торгову дію"""
        trade_info = f"TRADE: {symbol} {side} @ {price}" if all([symbol, side, price]) else ""
        full_message = f"{message} {trade_info}".strip()
        self._log("TRADE", full_message, "TRADING")
        
    def signal(self, message: str, symbol: str = None, signal: str = None, confidence: float = None):
        """Логує сигнал"""
        signal_info = f"SIGNAL: {symbol} {signal} ({confidence:.2f})" if all([symbol, signal, confidence is not None]) else ""
        full_message = f"{message} {signal_info}".strip()
        self._log("SIGNAL", full_message, "SIGNALS")
        
    def risk(self, message: str, risk_level: str = None, exposure: float = None):
        """Логує ризик-менеджмент"""
        risk_info = f"RISK: {risk_level} Exposure: {exposure:.2f} USDT" if all([risk_level, exposure is not None]) else ""
        full_message = f"{message} {risk_info}".strip()
        self._log("RISK", full_message, "RISK_MANAGEMENT")
        
    def analysis(self, message: str, analysis_type: str = None, result: str = None):
        """Логує аналіз"""
        analysis_info = f"ANALYSIS: {analysis_type} -> {result}" if all([analysis_type, result]) else ""
        full_message = f"{message} {analysis_info}".strip()
        self._log("ANALYSIS", full_message, "ANALYSIS")
        
    def _log(self, level: str, message: str, category: str):
        """Внутрішній метод логування"""
        timestamp = datetime.utcnow()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "level": level,
            "category": category,
            "message": message,
            "unix_timestamp": int(timestamp.timestamp())
        }
        
        # Додаємо в буфер
        with log_lock:
            bot_logs.append(log_entry)
        
        # Виводимо в консоль
        color_map = {
            "INFO": "\033[94m",      # Blue
            "WARNING": "\033[93m",   # Yellow
            "ERROR": "\033[91m",     # Red
            "SUCCESS": "\033[92m",   # Green
            "TRADE": "\033[95m",     # Magenta
            "SIGNAL": "\033[96m",    # Cyan
            "RISK": "\033[33m",      # Orange
            "ANALYSIS": "\033[36m"   # Light Blue
        }
        
        color = color_map.get(level, "\033[0m")
        reset = "\033[0m"
        
        # Форматуємо повідомлення для консолі
        console_message = f"{color}[{timestamp.strftime('%H:%M:%S')}] {level}: {message}{reset}"
        print(console_message)

# Глобальний екземпляр логера
bot_logger = BotLogger()

def get_bot_logs(limit: int = 50, category: str = None, level: str = None) -> List[Dict[str, Any]]:
    """
    Отримує логи бота з фільтрацією
    """
    with log_lock:
        logs = list(bot_logs)
    
    # Фільтруємо за категорією
    if category:
        logs = [log for log in logs if log["category"] == category]
    
    # Фільтруємо за рівнем
    if level:
        logs = [log for log in logs if log["level"] == level]
    
    # Повертаємо останні логи
    return logs[-limit:] if limit > 0 else logs

def clear_bot_logs():
    """Очищає логи бота"""
    with log_lock:
        bot_logs.clear()

def get_log_stats() -> Dict[str, Any]:
    """Отримує статистику логів"""
    with log_lock:
        logs = list(bot_logs)
    
    if not logs:
        return {
            "total_logs": 0,
            "categories": {},
            "levels": {},
            "recent_activity": False
        }
    
    # Статистика за категоріями
    categories = {}
    levels = {}
    
    for log in logs:
        categories[log["category"]] = categories.get(log["category"], 0) + 1
        levels[log["level"]] = levels.get(log["level"], 0) + 1
    
    # Перевіряємо чи є активність за останні 5 хвилин
    recent_time = datetime.utcnow() - timedelta(minutes=5)
    recent_logs = [log for log in logs if datetime.fromisoformat(log["timestamp"]) > recent_time]
    
    return {
        "total_logs": len(logs),
        "categories": categories,
        "levels": levels,
        "recent_activity": len(recent_logs) > 0,
        "recent_logs_count": len(recent_logs)
    }

