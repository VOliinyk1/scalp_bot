#!/usr/bin/env python3
"""
Скрипт для запуску торгового бота
"""

import os
import sys
import subprocess
from pathlib import Path
from services.logging_service import bot_logger

# Додаємо корінь проекту до шляху
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_env_file():
    """Перевіряє наявність .env файлу"""
    env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / ".env"
    if not env_path.exists():
        bot_logger.error("❌ Файл .env не знайдено!")
        bot_logger.info("📝 Створіть файл .env з наступними змінними:")
        bot_logger.info("""
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
        bot_logger.info("🗄️ Ініціалізація бази даних...")
        subprocess.run([sys.executable, "app/init_db.py"], check=True)
        bot_logger.success("✅ База даних ініціалізована")
        return True
    except subprocess.CalledProcessError as e:
        bot_logger.error(f"❌ Помилка ініціалізації БД: {e}")
        return False

def test_smart_money():
    """Тестує Smart Money модуль"""
    try:
        bot_logger.info("🧠 Тестування Smart Money модуля...")
        subprocess.run([sys.executable, "app/test_smart_money.py"], check=True)
        bot_logger.success("✅ Smart Money модуль працює")
        return True
    except subprocess.CalledProcessError as e:
        bot_logger.error(f"❌ Помилка тестування: {e}")
        return False

def start_server():
    """Запускає FastAPI сервер"""
    bot_logger.success("🚀 Запуск FastAPI сервера...")
    bot_logger.info("📱 Telegram бот буде доступний після запуску сервера")
    bot_logger.info("🌐 API документація: http://localhost:8000/docs")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        bot_logger.info("\n👋 Сервер зупинено")

def main():
    """Головна функція"""
    bot_logger.success("🤖 Trade Bot - Smart Money Trading Bot")
    bot_logger.info("=" * 50)
    
    # Перевіряємо .env файл
    if not check_env_file():
        return
    
    # Ініціалізуємо БД
    if not init_database():
        return
    
    # Тестуємо Smart Money
    if not test_smart_money():
        bot_logger.warning("⚠️ Продовжуємо без тестування...")
    
    # Запускаємо сервер
    start_server()

if __name__ == "__main__":
    main()
