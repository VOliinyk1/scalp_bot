# app/models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)  # Напр., USDTUSDC
    side = Column(Enum("BUY", "SELL", name="order_side"))
    price = Column(Float)
    quantity = Column(Float)
    status = Column(String)  # Напр., NEW, PARTIALLY_FILLED, FILLED, CANCELED
    order_id = Column(String, unique=True)  # Binance orderId
    created_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    side = Column(Enum("BUY", "SELL", name="trade_side"))
    price = Column(Float)
    quantity = Column(Float)
    trade_id = Column(String, unique=True)
    order_id = Column(String)  # Binance orderId
    executed_at = Column(DateTime, default=datetime.utcnow)

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)  # INFO, WARNING, ERROR
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
