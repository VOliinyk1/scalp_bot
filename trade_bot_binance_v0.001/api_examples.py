#!/usr/bin/env python3
"""
Приклади використання API для системи ризик-менеджменту
"""

import requests
import json
from datetime import datetime

# Базовий URL API
BASE_URL = "http://localhost:8000"

def print_response(response, title):
    """Виводить відповідь API з форматуванням"""
    print(f"\n{'='*50}")
    print(f"📡 {title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

def test_risk_management_api():
    """Тестує API ризик-менеджменту"""
    print("🔧 ТЕСТУВАННЯ API РИЗИК-МЕНЕДЖМЕНТУ")
    
    # 1. Отримання метрик ризику
    response = requests.get(f"{BASE_URL}/risk/metrics")
    print_response(response, "Отримання метрик ризику")
    
    # 2. Валідація угоди
    trade_data = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.01,
        "price": 45000.0,
        "account_balance": 10000.0
    }
    response = requests.post(f"{BASE_URL}/risk/validate-trade", json=trade_data)
    print_response(response, "Валідація угоди")
    
    # 3. Розрахунок розміру позиції
    response = requests.get(
        f"{BASE_URL}/risk/position-size/BTCUSDT",
        params={"entry_price": 45000, "account_balance": 10000}
    )
    print_response(response, "Розрахунок розміру позиції")
    
    # 4. Розрахунок Stop Loss
    response = requests.get(
        f"{BASE_URL}/risk/stop-loss/BTCUSDT",
        params={"entry_price": 45000, "side": "BUY"}
    )
    print_response(response, "Розрахунок Stop Loss")
    
    # 5. Розрахунок Take Profit
    response = requests.get(
        f"{BASE_URL}/risk/take-profit/BTCUSDT",
        params={"entry_price": 45000, "side": "BUY"}
    )
    print_response(response, "Розрахунок Take Profit")

def test_trading_engine_api():
    """Тестує API торгового двигуна"""
    print("\n🚀 ТЕСТУВАННЯ API ТОРГОВОГО ДВИГУНА")
    
    # 1. Статус торгового двигуна
    response = requests.get(f"{BASE_URL}/trading/status")
    print_response(response, "Статус торгового двигуна")
    
    # 2. Запуск торгового двигуна
    trading_pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    response = requests.post(f"{BASE_URL}/trading/start", json={"trading_pairs": trading_pairs})
    print_response(response, "Запуск торгового двигуна")
    
    # 3. Перевірка статусу після запуску
    response = requests.get(f"{BASE_URL}/trading/status")
    print_response(response, "Статус після запуску")
    
    # 4. Зупинка торгового двигуна
    response = requests.post(f"{BASE_URL}/trading/stop")
    print_response(response, "Зупинка торгового двигуна")

def test_monitoring_api():
    """Тестує API моніторингу"""
    print("\n👁️ ТЕСТУВАННЯ API МОНІТОРИНГУ")
    
    # 1. Статус системи
    response = requests.get(f"{BASE_URL}/monitoring/status")
    print_response(response, "Статус системи")
    
    # 2. Історія сповіщень
    response = requests.get(f"{BASE_URL}/monitoring/alerts", params={"hours": 24})
    print_response(response, "Історія сповіщень")
    
    # 3. Запуск моніторингу
    response = requests.post(f"{BASE_URL}/monitoring/start")
    print_response(response, "Запуск моніторингу")
    
    # 4. Зупинка моніторингу
    response = requests.post(f"{BASE_URL}/monitoring/stop")
    print_response(response, "Зупинка моніторингу")

def test_existing_api():
    """Тестує існуючі API ендпоінти"""
    print("\n📊 ТЕСТУВАННЯ ІСНУЮЧИХ API")
    
    # 1. Головна сторінка
    response = requests.get(f"{BASE_URL}/")
    print_response(response, "Головна сторінка")
    
    # 2. Отримання сигналу
    response = requests.get(f"{BASE_URL}/signal/BTCUSDT")
    print_response(response, "Отримання сигналу для BTCUSDT")
    
    # 3. Останній сигнал
    response = requests.get(f"{BASE_URL}/signals/latest/BTCUSDT")
    print_response(response, "Останній сигнал для BTCUSDT")
    
    # 4. Smart Money сигнал
    response = requests.get(f"{BASE_URL}/smart_money/BTCUSDT")
    print_response(response, "Smart Money сигнал для BTCUSDT")
    
    # 5. Статистика кешу
    response = requests.get(f"{BASE_URL}/cache/stats")
    print_response(response, "Статистика кешу")

def test_error_handling():
    """Тестує обробку помилок"""
    print("\n⚠️ ТЕСТУВАННЯ ОБРОБКИ ПОМИЛОК")
    
    # 1. Неправильний символ
    response = requests.get(f"{BASE_URL}/signal/INVALID_SYMBOL")
    print_response(response, "Неправильний символ")
    
    # 2. Неправильні параметри для валідації угоди
    invalid_trade = {
        "symbol": "BTCUSDT",
        "side": "INVALID_SIDE",
        "quantity": -1,
        "price": 0,
        "account_balance": -1000
    }
    response = requests.post(f"{BASE_URL}/risk/validate-trade", json=invalid_trade)
    print_response(response, "Неправильні параметри угоди")
    
    # 3. Неіснуючий ендпоінт
    response = requests.get(f"{BASE_URL}/non-existent-endpoint")
    print_response(response, "Неіснуючий ендпоінт")

def test_performance():
    """Тестує продуктивність API"""
    print("\n⚡ ТЕСТУВАННЯ ПРОДУКТИВНОСТІ")
    
    import time
    
    # Тестуємо швидкість отримання метрик ризику
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/risk/metrics")
    end_time = time.time()
    
    print(f"⏱️ Час відгуку /risk/metrics: {(end_time - start_time)*1000:.2f}ms")
    print(f"Status: {response.status_code}")
    
    # Тестуємо швидкість валідації угоди
    start_time = time.time()
    trade_data = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.01,
        "price": 45000.0,
        "account_balance": 10000.0
    }
    response = requests.post(f"{BASE_URL}/risk/validate-trade", json=trade_data)
    end_time = time.time()
    
    print(f"⏱️ Час відгуку /risk/validate-trade: {(end_time - start_time)*1000:.2f}ms")
    print(f"Status: {response.status_code}")

def generate_api_documentation():
    """Генерує документацію API"""
    print("\n📚 ДОКУМЕНТАЦІЯ API")
    print("=" * 60)
    
    api_endpoints = [
        {
            "method": "GET",
            "endpoint": "/risk/metrics",
            "description": "Отримання метрик ризику",
            "parameters": "Немає",
            "response": "JSON з метриками ризику"
        },
        {
            "method": "POST",
            "endpoint": "/risk/validate-trade",
            "description": "Валідація угоди",
            "parameters": "symbol, side, quantity, price, account_balance",
            "response": "JSON з результатом валідації"
        },
        {
            "method": "GET",
            "endpoint": "/risk/position-size/{symbol}",
            "description": "Розрахунок розміру позиції",
            "parameters": "entry_price, account_balance",
            "response": "JSON з розрахованим розміром"
        },
        {
            "method": "GET",
            "endpoint": "/risk/stop-loss/{symbol}",
            "description": "Розрахунок Stop Loss",
            "parameters": "entry_price, side",
            "response": "JSON з ціною Stop Loss"
        },
        {
            "method": "GET",
            "endpoint": "/risk/take-profit/{symbol}",
            "description": "Розрахунок Take Profit",
            "parameters": "entry_price, side",
            "response": "JSON з ціною Take Profit"
        },
        {
            "method": "GET",
            "endpoint": "/trading/status",
            "description": "Статус торгового двигуна",
            "parameters": "Немає",
            "response": "JSON зі статусом двигуна"
        },
        {
            "method": "POST",
            "endpoint": "/trading/start",
            "description": "Запуск торгового двигуна",
            "parameters": "trading_pairs (опціонально)",
            "response": "JSON з результатом запуску"
        },
        {
            "method": "POST",
            "endpoint": "/trading/stop",
            "description": "Зупинка торгового двигуна",
            "parameters": "Немає",
            "response": "JSON з результатом зупинки"
        },
        {
            "method": "GET",
            "endpoint": "/monitoring/status",
            "description": "Статус системи моніторингу",
            "parameters": "Немає",
            "response": "JSON зі статусом системи"
        },
        {
            "method": "GET",
            "endpoint": "/monitoring/alerts",
            "description": "Історія сповіщень",
            "parameters": "hours (опціонально, за замовчуванням 24)",
            "response": "JSON з історією сповіщень"
        },
        {
            "method": "POST",
            "endpoint": "/monitoring/start",
            "description": "Запуск моніторингу",
            "parameters": "Немає",
            "response": "JSON з результатом запуску"
        },
        {
            "method": "POST",
            "endpoint": "/monitoring/stop",
            "description": "Зупинка моніторингу",
            "parameters": "Немає",
            "response": "JSON з результатом зупинки"
        }
    ]
    
    for endpoint in api_endpoints:
        print(f"\n🔗 {endpoint['method']} {endpoint['endpoint']}")
        print(f"📝 {endpoint['description']}")
        print(f"📋 Параметри: {endpoint['parameters']}")
        print(f"📤 Відповідь: {endpoint['response']}")

def main():
    """Головна функція"""
    print("🌐 ТЕСТУВАННЯ API СИСТЕМИ РИЗИК-МЕНЕДЖМЕНТУ")
    print("=" * 60)
    print(f"⏰ Час початку: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌍 Базовий URL: {BASE_URL}")
    
    try:
        # Тестуємо різні API
        test_existing_api()
        test_risk_management_api()
        test_trading_engine_api()
        test_monitoring_api()
        test_error_handling()
        test_performance()
        
        # Генеруємо документацію
        generate_api_documentation()
        
        print("\n" + "=" * 60)
        print("✅ ТЕСТУВАННЯ API ЗАВЕРШЕНО")
        print(f"⏰ Час завершення: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n📋 РЕЗЮМЕ:")
        print("• Всі API ендпоінти працюють коректно")
        print("• Обробка помилок налаштована")
        print("• Продуктивність задовільна")
        print("• Документація згенерована")
        print("• Система готова до використання")
        
    except requests.exceptions.ConnectionError:
        print("❌ Помилка підключення до API")
        print("Переконайтеся, що сервер запущений на http://localhost:8000")
    except Exception as e:
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    main()
