# init_db.py
import sys
import os

# Додаємо шлях до модуля app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from models import Base
from config import DB_URL

if __name__ == "__main__":
    try:
        print("🗄️ Створення таблиць бази даних...")
        Base.metadata.create_all(bind=engine)
        print("✅ Таблиці створені успішно!")
        print(f"📊 База даних: {DB_URL}")
    except Exception as e:
        print(f"❌ Помилка створення таблиць: {e}")
        sys.exit(1)
