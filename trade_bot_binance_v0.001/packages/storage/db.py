from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from packages.core.config import settings

engine = create_engine(settings.DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    Base.metadata.create_all(bind=engine)
