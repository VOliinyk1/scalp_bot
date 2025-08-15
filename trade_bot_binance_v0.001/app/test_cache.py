#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки роботи кешування
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.cache import trading_cache, CACHE_TTL
from app.services.smart_money import get_smart_money_signal

def test_cache_basic():
    """Тестуємо базові функції кешу"""
    print("🧪 Тестування базових функцій кешу...")
    
    # Тест 1: Збереження та отримання даних
    test_data = {"test": "data", "number": 42}
    trading_cache.set(test_data, 60, "test", key="value")
    
    cached_data = trading_cache.get("test", key="value")
    if cached_data == test_data:
        print("✅ Тест 1: Збереження та отримання - УСПІШНО")
    else:
        print("❌ Тест 1: Збереження та отримання - ПОМИЛКА")
    
    # Тест 2: Перевірка TTL
    trading_cache.set(test_data, 1, "test_ttl", key="value")  # 1 секунда
    time.sleep(2)  # Чекаємо 2 секунди
    
    cached_data = trading_cache.get("test_ttl", key="value")
    if cached_data is None:
        print("✅ Тест 2: TTL (застаріння) - УСПІШНО")
    else:
        print("❌ Тест 2: TTL (застаріння) - ПОМИЛКА")

def test_cache_performance():
    """Тестуємо продуктивність кешу"""
    print("\n⚡ Тестування продуктивності кешу...")
    
    symbol = "BTCUSDT"
    
    # Перший запит (без кешу)
    start_time = time.time()
    result1 = get_smart_money_signal(symbol)
    time1 = time.time() - start_time
    
    # Другий запит (з кешу)
    start_time = time.time()
    result2 = get_smart_money_signal(symbol)
    time2 = time.time() - start_time
    
    print(f"⏱️ Час першого запиту: {time1:.3f} сек")
    print(f"⏱️ Час другого запиту: {time2:.3f} сек")
    
    if time2 > 0:
        print(f"🚀 Прискорення: {time1/time2:.1f}x")
    else:
        print("🚀 Прискорення: ∞ (мгновенний кеш)")
    
    if time2 < time1 * 0.5:  # Другий запит має бути значно швидшим
        print("✅ Продуктивність кешу - УСПІШНО")
    else:
        print("❌ Продуктивність кешу - ПОМИЛКА")

def test_cache_stats():
    """Тестуємо статистику кешу"""
    print("\n📊 Тестування статистики кешу...")
    
    # Очищаємо кеш для чистих тестів
    trading_cache.clear()
    
    # Робимо кілька запитів
    for i in range(3):
        get_smart_money_signal("BTCUSDT")
        get_smart_money_signal("ETHUSDT")
    
    stats = trading_cache.get_stats()
    
    print(f"📈 Статистика кешу:")
    print(f"   Запити: {stats['total_requests']}")
    print(f"   Попадання: {stats['hits']}")
    print(f"   Промахи: {stats['misses']}")
    print(f"   Ефективність: {stats['hit_rate']:.1%}")
    print(f"   Розмір: {stats['size']} записів")
    
    if stats['hit_rate'] > 0:
        print("✅ Статистика кешу - УСПІШНО")
    else:
        print("❌ Статистика кешу - ПОМИЛКА")

def test_cache_cleanup():
    """Тестуємо очищення кешу"""
    print("\n🧹 Тестування очищення кешу...")
    
    # Додаємо тестові дані
    for i in range(10):
        trading_cache.set(f"data_{i}", 3600, "test_cleanup", index=i)
    
    initial_size = len(trading_cache._cache)
    print(f"📦 Розмір кешу до очищення: {initial_size}")
    
    # Очищаємо кеш
    trading_cache.clear()
    
    final_size = len(trading_cache._cache)
    print(f"📦 Розмір кешу після очищення: {final_size}")
    
    if final_size == 0:
        print("✅ Очищення кешу - УСПІШНО")
    else:
        print("❌ Очищення кешу - ПОМИЛКА")

def main():
    """Головна функція тестування"""
    print("🧪 Тестування системи кешування")
    print("=" * 50)
    
    try:
        test_cache_basic()
        test_cache_performance()
        test_cache_stats()
        test_cache_cleanup()
        
        print("\n🎉 Всі тести завершено!")
        
    except Exception as e:
        print(f"\n❌ Помилка під час тестування: {e}")

if __name__ == "__main__":
    main()
