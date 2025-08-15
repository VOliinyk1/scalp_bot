# app/services/cache.py
"""
Модуль кешування для зберігання результатів аналізу та зменшення навантаження на API
"""

import time
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class CacheEntry:
    """Запис в кеші"""
    data: Any
    timestamp: float
    ttl: int  # Time to live в секундах
    
    def is_expired(self) -> bool:
        """Перевіряє чи застарів запис"""
        return time.time() - self.timestamp > self.ttl

class TradingCache:
    """Кеш для торгових даних"""
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Генерує ключ для кешу на основі параметрів"""
        # Сортуємо параметри для стабільності ключа
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        return f"{prefix}:{hashlib.md5(param_str.encode()).hexdigest()}"
    
    def get(self, prefix: str, **kwargs) -> Optional[Any]:
        """Отримує дані з кешу"""
        key = self._generate_key(prefix, **kwargs)
        
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                self._stats["hits"] += 1
                return entry.data
            else:
                # Видаляємо застарілий запис
                del self._cache[key]
                self._stats["evictions"] += 1
        
        self._stats["misses"] += 1
        return None
    
    def set(self, data: Any, ttl: int, prefix: str, **kwargs) -> None:
        """Зберігає дані в кеш"""
        key = self._generate_key(prefix, **kwargs)
        
        # Видаляємо старі записи якщо кеш переповнений
        if len(self._cache) > 1000:  # Максимум 1000 записів
            self._cleanup_expired()
            if len(self._cache) > 1000:
                # Видаляємо найстаріші записи
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k].timestamp)
                del self._cache[oldest_key]
                self._stats["evictions"] += 1
        
        self._cache[key] = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl
        )
        self._stats["sets"] += 1
    
    def _cleanup_expired(self) -> None:
        """Видаляє застарілі записи"""
        expired_keys = [
            key for key, entry in self._cache.items() 
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
            self._stats["evictions"] += 1
    
    def clear(self) -> None:
        """Очищає весь кеш"""
        self._cache.clear()
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """Отримує статистику кешу"""
        self._cleanup_expired()
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **self._stats,
            "hit_rate": round(hit_rate, 3),
            "size": len(self._cache),
            "total_requests": total_requests
        }

# Глобальний екземпляр кешу
trading_cache = TradingCache()

# Константи для TTL (Time To Live)
CACHE_TTL = {
    "ohlcv_1m": 60,      # 1 хвилина для 1m даних
    "ohlcv_5m": 300,     # 5 хвилин для 5m даних
    "ohlcv_15m": 900,    # 15 хвилин для 15m даних
    "ohlcv_1h": 3600,    # 1 година для 1h даних
    "ohlcv_4h": 14400,   # 4 години для 4h даних
    "orderbook": 30,     # 30 секунд для ордербука
    "smart_money_signal": 300,  # 5 хвилин для Smart Money сигналів
    "ai_signal": 300,    # 5 хвилин для AI сигналів
    "news_sentiment": 1800,  # 30 хвилин для сентименту новин
}
