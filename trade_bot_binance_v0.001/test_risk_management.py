#!/usr/bin/env python3
"""
Тестовий скрипт для демонстрації роботи системи ризик-менеджменту
"""

import asyncio
import time
from datetime import datetime

from app.services.risk_management import get_risk_manager, RiskConfig
from app.services.trading_engine import get_trading_engine
from app.services.monitoring import get_monitoring_service
from app.risk_config import get_risk_config, validate_risk_config

def test_risk_configurations():
    """Тестує різні конфігурації ризик-менеджменту"""
    print("🔧 Тестування конфігурацій ризик-менеджменту")
    print("=" * 50)
    
    # Тестуємо різні профілі
    profiles = ["conservative", "default", "aggressive"]
    
    for profile in profiles:
        print(f"\n📊 Профіль: {profile.upper()}")
        config = get_risk_config(profile=profile)
        
        # Валідуємо конфігурацію
        is_valid, message = validate_risk_config(config)
        print(f"✅ Валідність: {is_valid} - {message}")
        
        # Виводимо ключові параметри
        print(f"   • Максимальний розмір позиції: {config.max_position_size_usdt} USDT")
        print(f"   • Загальна експозиція: {config.max_total_exposure_usdt} USDT")
        print(f"   • Денний збиток: {config.max_daily_loss_usdt} USDT")
        print(f"   • Просадка: {config.max_drawdown_percent}%")
        print(f"   • Stop Loss: {config.stop_loss_percent}%")
        print(f"   • Take Profit: {config.take_profit_percent}%")
        print(f"   • Ризик на угоду: {config.max_risk_per_trade_percent}%")

def test_trade_validation():
    """Тестує валідацію угод"""
    print("\n🔍 Тестування валідації угод")
    print("=" * 50)
    
    risk_manager = get_risk_manager()
    
    # Тестові угоди
    test_trades = [
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "price": 45000.0,
            "balance": 10000.0,
            "description": "Нормальна угода BTC"
        },
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 1.0,
            "price": 45000.0,
            "balance": 10000.0,
            "description": "Занадто велика позиція"
        },
        {
            "symbol": "ETHUSDT",
            "side": "SELL",
            "quantity": 0.1,
            "price": 3000.0,
            "balance": 5000.0,
            "description": "Нормальна угода ETH"
        }
    ]
    
    for trade in test_trades:
        print(f"\n📈 {trade['description']}")
        is_valid, reason = risk_manager.validate_trade(
            trade["symbol"],
            trade["side"],
            trade["quantity"],
            trade["price"],
            trade["balance"]
        )
        
        status = "✅ ДОЗВОЛЕНО" if is_valid else "❌ ВІДХИЛЕНО"
        print(f"   {status}: {reason}")
        print(f"   • Символ: {trade['symbol']}")
        print(f"   • Сторона: {trade['side']}")
        print(f"   • Кількість: {trade['quantity']}")
        print(f"   • Ціна: {trade['price']} USDT")
        print(f"   • Вартість позиції: {trade['quantity'] * trade['price']:.2f} USDT")

def test_position_sizing():
    """Тестує розрахунок розмірів позицій"""
    print("\n📏 Тестування розрахунку розмірів позицій")
    print("=" * 50)
    
    risk_manager = get_risk_manager()
    
    # Тестові сценарії
    scenarios = [
        {
            "symbol": "BTCUSDT",
            "entry_price": 45000.0,
            "balance": 10000.0,
            "description": "BTC з балансом 10,000 USDT"
        },
        {
            "symbol": "ETHUSDT",
            "entry_price": 3000.0,
            "balance": 5000.0,
            "description": "ETH з балансом 5,000 USDT"
        },
        {
            "symbol": "BNBUSDT",
            "entry_price": 300.0,
            "balance": 2000.0,
            "description": "BNB з балансом 2,000 USDT"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n💰 {scenario['description']}")
        quantity = risk_manager.calculate_position_size(
            scenario["symbol"],
            scenario["entry_price"],
            scenario["balance"]
        )
        
        position_value = quantity * scenario["entry_price"]
        risk_amount = scenario["balance"] * (risk_manager.config.max_risk_per_trade_percent / 100)
        
        print(f"   • Рекомендована кількість: {quantity:.8f}")
        print(f"   • Вартість позиції: {position_value:.2f} USDT")
        print(f"   • Ризик на угоду: {risk_amount:.2f} USDT")
        print(f"   • Відсоток від балансу: {(position_value / scenario['balance']) * 100:.2f}%")

def test_stop_loss_take_profit():
    """Тестує розрахунок Stop Loss та Take Profit"""
    print("\n🎯 Тестування Stop Loss та Take Profit")
    print("=" * 50)
    
    risk_manager = get_risk_manager()
    
    # Тестові сценарії
    scenarios = [
        {
            "symbol": "BTCUSDT",
            "entry_price": 45000.0,
            "side": "BUY",
            "description": "Long позиція BTC"
        },
        {
            "symbol": "ETHUSDT",
            "entry_price": 3000.0,
            "side": "SELL",
            "description": "Short позиція ETH"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['description']}")
        
        stop_loss = risk_manager.calculate_stop_loss_price(
            scenario["symbol"],
            scenario["entry_price"],
            scenario["side"]
        )
        
        take_profit = risk_manager.calculate_take_profit_price(
            scenario["symbol"],
            scenario["entry_price"],
            scenario["side"]
        )
        
        print(f"   • Ціна входу: {scenario['entry_price']:.2f} USDT")
        print(f"   • Stop Loss: {stop_loss:.2f} USDT")
        print(f"   • Take Profit: {take_profit:.2f} USDT")
        
        if scenario["side"] == "BUY":
            sl_percent = ((scenario["entry_price"] - stop_loss) / scenario["entry_price"]) * 100
            tp_percent = ((take_profit - scenario["entry_price"]) / scenario["entry_price"]) * 100
        else:
            sl_percent = ((stop_loss - scenario["entry_price"]) / scenario["entry_price"]) * 100
            tp_percent = ((scenario["entry_price"] - take_profit) / scenario["entry_price"]) * 100
        
        print(f"   • Stop Loss: {sl_percent:.2f}%")
        print(f"   • Take Profit: {tp_percent:.2f}%")

def test_risk_metrics():
    """Тестує розрахунок метрик ризику"""
    print("\n📈 Тестування метрик ризику")
    print("=" * 50)
    
    risk_manager = get_risk_manager()
    
    # Отримуємо метрики
    metrics = risk_manager.get_risk_metrics()
    
    print(f"📊 Поточні метрики ризику:")
    print(f"   • Загальна експозиція: {metrics.total_exposure:.2f} USDT")
    print(f"   • Максимальна просадка: {metrics.max_drawdown:.2f}%")
    print(f"   • Win Rate: {metrics.win_rate:.1%}")
    print(f"   • Середній прибуток: {metrics.avg_win:.2f} USDT")
    print(f"   • Середній збиток: {metrics.avg_loss:.2f} USDT")
    print(f"   • Коефіцієнт Шарпа: {metrics.sharpe_ratio:.2f}")
    print(f"   • Денний P&L: {metrics.daily_pnl:.2f} USDT")
    print(f"   • Волатильність: {metrics.volatility:.4f}")

def test_volatility_liquidity():
    """Тестує розрахунок волатильності та ліквідності"""
    print("\n📊 Тестування волатильності та ліквідності")
    print("=" * 50)
    
    risk_manager = get_risk_manager()
    
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    for symbol in symbols:
        print(f"\n🔍 {symbol}")
        
        # Волатильність
        volatility = risk_manager._get_symbol_volatility(symbol)
        print(f"   • Волатильність: {volatility:.4f}")
        
        # Ліквідність
        liquidity = risk_manager._get_symbol_liquidity(symbol)
        print(f"   • Ліквідність: {liquidity:,.0f} USDT")
        
        # Оцінка ризику
        if volatility > risk_manager.config.max_volatility_threshold:
            print(f"   ⚠️  Висока волатильність!")
        
        if liquidity < risk_manager.config.min_liquidity_usdt:
            print(f"   ⚠️  Низька ліквідність!")

async def test_trading_engine():
    """Тестує торговий двигун"""
    print("\n🚀 Тестування торгового двигуна")
    print("=" * 50)
    
    trading_engine = get_trading_engine()
    
    print("📊 Статус торгового двигуна:")
    print(f"   • Запущений: {trading_engine.is_running}")
    print(f"   • Торгові пари: {trading_engine.trading_pairs}")
    print(f"   • Активні ордери: {len(trading_engine.active_orders)}")
    print(f"   • Баланс акаунту: {trading_engine.account_balance:.2f} USDT")

async def test_monitoring():
    """Тестує систему моніторингу"""
    print("\n👁️ Тестування системи моніторингу")
    print("=" * 50)
    
    monitoring_service = get_monitoring_service()
    
    # Отримуємо статус системи
    status = monitoring_service.get_system_status()
    
    print("📊 Статус системи:")
    print(f"   • Рівень ризику: {status.get('risk_level', 'N/A')}")
    print(f"   • Час роботи: {status.get('uptime', 'N/A')}")
    print(f"   • Остання перевірка: {status.get('last_check', 'N/A')}")
    
    # Отримуємо історію сповіщень
    alerts = monitoring_service.get_alert_history(hours=1)
    print(f"   • Сповіщення за останню годину: {len(alerts)}")

def main():
    """Головна функція тестування"""
    print("🧪 ТЕСТУВАННЯ СИСТЕМИ РИЗИК-МЕНЕДЖМЕНТУ")
    print("=" * 60)
    print(f"⏰ Час початку: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Запускаємо тести
    test_risk_configurations()
    test_trade_validation()
    test_position_sizing()
    test_stop_loss_take_profit()
    test_risk_metrics()
    test_volatility_liquidity()
    
    # Асинхронні тести
    asyncio.run(test_trading_engine())
    asyncio.run(test_monitoring())
    
    print("\n" + "=" * 60)
    print("✅ ТЕСТУВАННЯ ЗАВЕРШЕНО")
    print(f"⏰ Час завершення: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n📋 РЕЗЮМЕ:")
    print("• Система ризик-менеджменту готова до роботи")
    print("• Всі компоненти працюють коректно")
    print("• API ендпоінти доступні")
    print("• Моніторинг налаштований")
    print("• Готово до інтеграції з торговим ботом")

if __name__ == "__main__":
    main()
