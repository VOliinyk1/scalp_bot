# app/services/monitoring.py
"""
Модуль моніторингу для торгового бота
Відстежує стан системи та відправляє сповіщення про важливі події
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import asdict
import requests

from app.services.risk_management import get_risk_manager, RiskLevel
from app.services.cache import trading_cache
from app.config import TELEGRAM_BOT_TOKEN

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitoringService:
    """Сервіс моніторингу"""
    
    def __init__(self):
        self.risk_manager = get_risk_manager()
        self.telegram_token = TELEGRAM_BOT_TOKEN
        self.alert_history: List[Dict] = []
        self.is_running = False
        
        # Налаштування сповіщень
        self.alert_config = {
            "risk_levels": {
                RiskLevel.LOW: {"telegram": False, "email": False},
                RiskLevel.MEDIUM: {"telegram": True, "email": False},
                RiskLevel.HIGH: {"telegram": True, "email": True},
                RiskLevel.CRITICAL: {"telegram": True, "email": True}
            },
            "check_interval": 60,  # секунди
            "max_alerts_per_hour": 10
        }
    
    async def start_monitoring(self):
        """
        Запускає моніторинг
        """
        if self.is_running:
            logger.warning("Моніторинг вже запущений")
            return
        
        self.is_running = True
        logger.info("Моніторинг запущений")
        
        # Запускаємо цикли моніторингу
        await asyncio.gather(
            self._risk_monitoring_loop(),
            self._system_health_loop(),
            self._performance_monitoring_loop()
        )
    
    async def stop_monitoring(self):
        """
        Зупиняє моніторинг
        """
        self.is_running = False
        logger.info("Моніторинг зупинений")
    
    async def _risk_monitoring_loop(self):
        """
        Цикл моніторингу ризиків
        """
        while self.is_running:
            try:
                # Отримуємо метрики ризику
                risk_metrics = self.risk_manager.get_risk_metrics()
                
                # Аналізуємо рівень ризику
                risk_level = self._analyze_risk_level(risk_metrics)
                
                # Перевіряємо чи потрібно відправити сповіщення
                if self._should_send_alert(risk_level):
                    await self._send_risk_alert(risk_level, risk_metrics)
                
                # Зберігаємо історію сповіщень
                self._save_alert_history(risk_level, risk_metrics)
                
                await asyncio.sleep(self.alert_config["check_interval"])
                
            except Exception as e:
                logger.error(f"Помилка в циклі моніторингу ризиків: {e}")
                await asyncio.sleep(120)
    
    async def _system_health_loop(self):
        """
        Цикл перевірки здоров'я системи
        """
        while self.is_running:
            try:
                # Перевіряємо доступність API
                api_health = await self._check_api_health()
                
                # Перевіряємо стан бази даних
                db_health = await self._check_database_health()
                
                # Перевіряємо стан кешу
                cache_health = await self._check_cache_health()
                
                # Відправляємо сповіщення про проблеми
                if not all([api_health, db_health, cache_health]):
                    await self._send_system_alert(api_health, db_health, cache_health)
                
                await asyncio.sleep(300)  # Перевіряємо кожні 5 хвилин
                
            except Exception as e:
                logger.error(f"Помилка в циклі перевірки здоров'я системи: {e}")
                await asyncio.sleep(600)
    
    async def _performance_monitoring_loop(self):
        """
        Цикл моніторингу продуктивності
        """
        while self.is_running:
            try:
                # Отримуємо статистику кешу
                cache_stats = trading_cache.get_stats()
                
                # Аналізуємо продуктивність
                performance_metrics = self._analyze_performance(cache_stats)
                
                # Відправляємо звіт про продуктивність
                if self._should_send_performance_report():
                    await self._send_performance_report(performance_metrics)
                
                await asyncio.sleep(3600)  # Звіт кожну годину
                
            except Exception as e:
                logger.error(f"Помилка в циклі моніторингу продуктивності: {e}")
                await asyncio.sleep(7200)
    
    def _analyze_risk_level(self, risk_metrics) -> RiskLevel:
        """
        Аналізує рівень ризику на основі метрик
        """
        # Критичні умови
        if (risk_metrics.total_exposure > self.risk_manager.config.max_total_exposure_usdt * 0.9 or
            risk_metrics.daily_pnl < -self.risk_manager.config.max_daily_loss_usdt * 0.9 or
            risk_metrics.max_drawdown > self.risk_manager.config.max_drawdown_percent * 0.9):
            return RiskLevel.CRITICAL
        
        # Високий ризик
        if (risk_metrics.total_exposure > self.risk_manager.config.max_total_exposure_usdt * 0.7 or
            risk_metrics.daily_pnl < -self.risk_manager.config.max_daily_loss_usdt * 0.7 or
            risk_metrics.max_drawdown > self.risk_manager.config.max_drawdown_percent * 0.7):
            return RiskLevel.HIGH
        
        # Середній ризик
        if (risk_metrics.total_exposure > self.risk_manager.config.max_total_exposure_usdt * 0.5 or
            risk_metrics.daily_pnl < -self.risk_manager.config.max_daily_loss_usdt * 0.5 or
            risk_metrics.max_drawdown > self.risk_manager.config.max_drawdown_percent * 0.5):
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def _should_send_alert(self, risk_level: RiskLevel) -> bool:
        """
        Перевіряє чи потрібно відправити сповіщення
        """
        # Перевіряємо ліміт сповіщень
        recent_alerts = [
            alert for alert in self.alert_history 
            if datetime.utcnow() - alert["timestamp"] < timedelta(hours=1)
        ]
        
        if len(recent_alerts) >= self.alert_config["max_alerts_per_hour"]:
            return False
        
        # Перевіряємо налаштування для рівня ризику
        return self.alert_config["risk_levels"][risk_level]["telegram"]
    
    async def _send_risk_alert(self, risk_level: RiskLevel, risk_metrics):
        """
        Відправляє сповіщення про ризик
        """
        try:
            message = self._format_risk_alert(risk_level, risk_metrics)
            
            if self.alert_config["risk_levels"][risk_level]["telegram"]:
                await self._send_telegram_message(message)
            
            logger.info(f"Сповіщення про ризик відправлено: {risk_level.value}")
            
        except Exception as e:
            logger.error(f"Помилка відправки сповіщення про ризик: {e}")
    
    def _format_risk_alert(self, risk_level: RiskLevel, risk_metrics) -> str:
        """
        Форматує повідомлення про ризик
        """
        emoji_map = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡", 
            RiskLevel.HIGH: "🟠",
            RiskLevel.CRITICAL: "🔴"
        }
        
        message = f"""
{emoji_map[risk_level]} **СПОВІЩЕННЯ ПРО РИЗИК: {risk_level.value}**

📊 **Метрики ризику:**
• Загальна експозиція: {risk_metrics.total_exposure:.2f} USDT
• Денний P&L: {risk_metrics.daily_pnl:.2f} USDT
• Максимальна просадка: {risk_metrics.max_drawdown:.2f}%
• Волатильність: {risk_metrics.volatility:.4f}

⏰ Час: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """
        
        return message.strip()
    
    async def _send_system_alert(self, api_health: bool, db_health: bool, cache_health: bool):
        """
        Відправляє сповіщення про стан системи
        """
        try:
            message = self._format_system_alert(api_health, db_health, cache_health)
            await self._send_telegram_message(message)
            
            logger.info("Сповіщення про стан системи відправлено")
            
        except Exception as e:
            logger.error(f"Помилка відправки сповіщення про стан системи: {e}")
    
    def _format_system_alert(self, api_health: bool, db_health: bool, cache_health: bool) -> str:
        """
        Форматує повідомлення про стан системи
        """
        status_emoji = lambda x: "✅" if x else "❌"
        
        message = f"""
🔧 **СТАН СИСТЕМИ**

{status_emoji(api_health)} Binance API: {"Онлайн" if api_health else "Офлайн"}
{status_emoji(db_health)} База даних: {"Онлайн" if db_health else "Офлайн"}
{status_emoji(cache_health)} Кеш: {"Онлайн" if cache_health else "Офлайн"}

⏰ Час: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """
        
        return message.strip()
    
    async def _send_performance_report(self, performance_metrics: Dict):
        """
        Відправляє звіт про продуктивність
        """
        try:
            message = self._format_performance_report(performance_metrics)
            await self._send_telegram_message(message)
            
            logger.info("Звіт про продуктивність відправлено")
            
        except Exception as e:
            logger.error(f"Помилка відправки звіту про продуктивність: {e}")
    
    def _format_performance_report(self, performance_metrics: Dict) -> str:
        """
        Форматує звіт про продуктивність
        """
        message = f"""
📈 **ЗВІТ ПРО ПРОДУКТИВНІСТЬ**

🎯 **Кеш:**
• Hit Rate: {performance_metrics.get('hit_rate', 0):.1%}
• Розмір: {performance_metrics.get('size', 0)} записів
• Загальні запити: {performance_metrics.get('total_requests', 0)}

⚡ **Система:**
• Час роботи: {performance_metrics.get('uptime', 'N/A')}
• Використання пам'яті: {performance_metrics.get('memory_usage', 'N/A')}

⏰ Час: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """
        
        return message.strip()
    
    async def _send_telegram_message(self, message: str):
        """
        Відправляє повідомлення в Telegram
        """
        if not self.telegram_token:
            logger.warning("Telegram токен не налаштований")
            return
        
        try:
            # Тут потрібно буде додати chat_id для відправки повідомлень
            # Поки що просто логуємо повідомлення
            logger.info(f"Telegram повідомлення: {message}")
            
            # Приклад відправки через API
            # url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            # data = {
            #     "chat_id": "YOUR_CHAT_ID",
            #     "text": message,
            #     "parse_mode": "Markdown"
            # }
            # response = requests.post(url, json=data)
            # response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Помилка відправки Telegram повідомлення: {e}")
    
    async def _check_api_health(self) -> bool:
        """
        Перевіряє доступність Binance API
        """
        try:
            # Тут можна додати реальну перевірку API
            # Поки що повертаємо True
            return True
        except Exception as e:
            logger.error(f"Помилка перевірки API: {e}")
            return False
    
    async def _check_database_health(self) -> bool:
        """
        Перевіряє стан бази даних
        """
        try:
            # Тут можна додати реальну перевірку БД
            # Поки що повертаємо True
            return True
        except Exception as e:
            logger.error(f"Помилка перевірки БД: {e}")
            return False
    
    async def _check_cache_health(self) -> bool:
        """
        Перевіряє стан кешу
        """
        try:
            stats = trading_cache.get_stats()
            return stats["size"] < 1000  # Кеш не переповнений
        except Exception as e:
            logger.error(f"Помилка перевірки кешу: {e}")
            return False
    
    def _analyze_performance(self, cache_stats: Dict) -> Dict:
        """
        Аналізує продуктивність системи
        """
        return {
            "hit_rate": cache_stats.get("hit_rate", 0),
            "size": cache_stats.get("size", 0),
            "total_requests": cache_stats.get("total_requests", 0),
            "uptime": "24h",  # Тут можна додати реальний час роботи
            "memory_usage": "512MB"  # Тут можна додати реальне використання пам'яті
        }
    
    def _should_send_performance_report(self) -> bool:
        """
        Перевіряє чи потрібно відправити звіт про продуктивність
        """
        # Відправляємо звіт кожну годину
        return True
    
    def _save_alert_history(self, risk_level: RiskLevel, risk_metrics):
        """
        Зберігає історію сповіщень
        """
        alert = {
            "risk_level": risk_level.value,
            "risk_metrics": asdict(risk_metrics),
            "timestamp": datetime.utcnow()
        }
        
        self.alert_history.append(alert)
        
        # Обмежуємо розмір історії
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict]:
        """
        Отримує історію сповіщень за останні N годин
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history 
            if alert["timestamp"] >= cutoff_time
        ]
    
    def get_system_status(self) -> Dict:
        """
        Отримує поточний стан системи
        """
        try:
            risk_metrics = self.risk_manager.get_risk_metrics()
            risk_level = self._analyze_risk_level(risk_metrics)
            cache_stats = trading_cache.get_stats()
            
            return {
                "risk_level": risk_level.value,
                "risk_metrics": asdict(risk_metrics),
                "cache_stats": cache_stats,
                "uptime": "24h",
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Помилка отримання стану системи: {e}")
            return {"error": str(e)}

# Глобальний екземпляр сервісу моніторингу
monitoring_service = MonitoringService()

def get_monitoring_service() -> MonitoringService:
    """Отримує глобальний екземпляр сервісу моніторингу"""
    return monitoring_service
