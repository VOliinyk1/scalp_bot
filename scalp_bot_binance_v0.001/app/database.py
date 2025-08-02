# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DB_URL

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функція для використання сесії в FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
