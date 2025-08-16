#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки отримання реального балансу з Binance
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.binance_api import BinanceAPI

def test_balance():
    print("🔍 Тестування отримання балансу...")
    
    try:
        api = BinanceAPI()
        balance = api.get_account_balance()
        
        if balance:
            print(f"✅ Успішно отримано баланс!")
            print(f"📊 Кількість активів: {len(balance.get('balances', []))}")
            print(f"💰 Загальна вартість: ${balance.get('total_portfolio_value', 0):.2f}")
            print(f"🏦 Тип акаунту: {balance.get('account_type', 'Невідомо')}")
            
            # Показуємо топ-5 активів
            balances = balance.get('balances', [])
            if balances:
                print("\n📈 Топ-5 активів за вартістю:")
                for i, asset in enumerate(balances[:5], 1):
                    print(f"  {i}. {asset['asset']}: {asset['total']:.6f} (${asset['usdt_value']:.2f})")
            
            return True
        else:
            print("❌ Не вдалося отримати баланс")
            return False
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False

if __name__ == "__main__":
    test_balance()
