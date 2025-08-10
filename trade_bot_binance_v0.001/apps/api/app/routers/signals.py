from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from packages.storage.models import Signal
from ..deps import get_db

router = APIRouter(prefix="/signals", tags=["signals"])

@router.get("/latest")
def latest(db=Depends(get_db)):
    row = db.execute(select(Signal).order_by(desc(Signal.ts)).limit(1)).scalar_one_or_none()
    return {} if row is None else {
        "ts": row.ts, "symbol": row.symbol, "timeframe": row.timeframe,
        "signal": row.signal, "p_buy": row.p_buy, "p_sell": row.p_sell
    }

@router.get("/health")
def health():
    return {"status": "ok"}
