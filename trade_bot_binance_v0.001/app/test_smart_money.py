#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки Smart Money модуля
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.smart_money import get_smart_money_signal, analyze_top_traders

def test_smart_money():
    """Тестуємо Smart Money аналіз"""
    print("🧠 Тестування Smart Money модуля...")
    
    # Тестуємо різні символи
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    for symbol in symbols:
        print(f"\n📊 Тестуємо {symbol}:")
        
        try:
            # Тестуємо основну функцію
            result = get_smart_money_signal(symbol)
            print(f"✅ Результат: {result['signal']}")
            print(f"   BUY: {result['p_buy']:.3f}")
            print(f"   SELL: {result['p_sell']:.3f}")
            print(f"   Впевненість: {result['confidence']:.3f}")
            
            # Тестуємо функцію для ai_signals
            ai_result = analyze_top_traders(symbol)
            print(f"   AI формат: {ai_result['signal']} (conf: {ai_result['confidence']})")
            
        except Exception as e:
            print(f"❌ Помилка для {symbol}: {e}")
    
    print("\n🎉 Тестування завершено!")

if __name__ == "__main__":
    test_smart_money()
