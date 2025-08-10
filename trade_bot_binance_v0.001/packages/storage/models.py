from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Float, Integer, DateTime, func

Base = declarative_base()

class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[int] = mapped_column(BigInteger, index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(10))
    signal: Mapped[str] = mapped_column(String(10))
    p_buy: Mapped[float] = mapped_column(Float)
    p_sell: Mapped[float] = mapped_column(Float)
    ob_imbalance: Mapped[float] = mapped_column(Float)
    top_traders_ratio: Mapped[float] = mapped_column(Float)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())
