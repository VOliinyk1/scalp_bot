#!/usr/bin/env python3
"""
Скрипт для запуску торгового бота
"""

import os
import sys
import subprocess
from pathlib import Path

# Додаємо корінь проекту до шляху
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_env_file():
    """Перевіряє наявність .env файлу"""
    env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".env"
    if not env_path.exists():
        print("❌ Файл .env не знайдено!")
        print("📝 Створіть файл .env з наступними змінними:")
        print("""
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
DATABASE_URL=sqlite:///./trading_bot.db
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
FASTAPI_URL=http://localhost:8000
        """)
        return False
    return True

def init_database():
    """Ініціалізує базу даних"""
    try:
        print("🗄️ Ініціалізація бази даних...")
        subprocess.run([sys.executable, "app/init_db.py"], check=True)
        print("✅ База даних ініціалізована")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Помилка ініціалізації БД: {e}")
        return False

def test_smart_money():
    """Тестує Smart Money модуль"""
    try:
        print("🧠 Тестування Smart Money модуля...")
        subprocess.run([sys.executable, "app/test_smart_money.py"], check=True)
        print("✅ Smart Money модуль працює")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Помилка тестування: {e}")
        return False

def start_server():
    """Запускає FastAPI сервер"""
    print("🚀 Запуск FastAPI сервера...")
    print("📱 Telegram бот буде доступний після запуску сервера")
    print("🌐 API документація: http://localhost:8000/docs")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n👋 Сервер зупинено")

def main():
    """Головна функція"""
    print("🤖 Trade Bot - Smart Money Trading Bot")
    print("=" * 50)
    
    # Перевіряємо .env файл
    if not check_env_file():
        return
    
    # Ініціалізуємо БД
    if not init_database():
        return
    
    # Тестуємо Smart Money
    if not test_smart_money():
        print("⚠️ Продовжуємо без тестування...")
    
    # Запускаємо сервер
    start_server()

if __name__ == "__main__":
    main()
