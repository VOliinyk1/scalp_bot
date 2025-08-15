# =============================================================================
# main.py
# 
# Entry point for the FastAPI application.
# Sets up API endpoints for trading signals, configures CORS, and launches
# the Telegram bot in a separate thread.
# =============================================================================

import threading
import datetime

from fastapi import FastAPI, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Optional
from pydantic import BaseModel

from app.services.ai_signals import detect_signal
from app.database import get_db
from app.models import Signal
from app.telegram_bot import start_telegram_bot
from app.database import SessionLocal
from app.services.risk_management import get_risk_manager
from app.services.trading_engine import get_trading_engine
from app.services.monitoring import get_monitoring_service
from app.services.analytics import get_analytics_service

# Pydantic models
class TradingStartRequest(BaseModel):
    trading_pairs: Optional[List[str]] = None

class TradingStopRequest(BaseModel):
    pass

class MonitoringStartRequest(BaseModel):
    pass

class MonitoringStopRequest(BaseModel):
    pass

class CacheClearRequest(BaseModel):
    pass

app = FastAPI(title="Trade Bot")

# Configure CORS middleware to allow requests from any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def main():
    """
    Root endpoint.
    Returns the dashboard HTML page.
    """
    return FileResponse("app/static/index.html")

@app.get("/api/health")
def health_check():
    """
    Health check endpoint.
    Returns a simple greeting message to verify the API is running.
    """
    return {"message": "Hello, FastAPI!", "status": "healthy"}

@app.get("/signal/{symbol}")
def get_signal(symbol: str):
    """
    Get trading signal for a given symbol (e.g., BTCUSDT, ETHUSDT).
    Calls the AI signal detection service and returns the result.
    """
    result = detect_signal(symbol.upper())
    return result

@app.get("/signals/latest/{symbol}")
def latest_signal(symbol: str, db: Session = Depends(get_db)):
    """
    Get the latest trading signal for a given symbol from the database.
    Returns signal details or None if no signal is found.
    """
    row = (db.query(Signal)
             .filter(Signal.symbol == symbol.upper())
             .order_by(Signal.id.desc())
             .first())
    if not row:
        return {"symbol": symbol.upper(), "latest": None}
    return {
        "symbol": row.symbol,
        "final_signal": row.final_signal,
        "weights": row.weights,
        "details": row.details,
        "created_at": row.created_at.isoformat()
    }

@app.get("/signals/latest")
def latest(db=Depends(get_db)):
    row = db.execute(select(Signal).order_by(desc(Signal.created_at)).limit(1)).scalar_one_or_none()
    return {} if row is None else {
        "ts": row.created_at, "symbol": row.symbol, "signal": row.final_signal,
        "weights": row.weights, "details": row.details
    }

@app.get("/smart_money/{symbol}")
def get_smart_money_signal(symbol: str):
    """
    Get Smart Money analysis for a given symbol.
    Returns detailed Smart Money signal with probabilities and indicators.
    """
    try:
        from app.services.smart_money import get_smart_money_signal as sm_signal
        result = sm_signal(symbol.upper())
        return result
    except Exception as e:
        return {
            "success": False,
            "symbol": symbol.upper(),
            "error": str(e),
            "signal": "HOLD"
        }

@app.get("/cache/stats")
def get_cache_stats():
    """
    Get cache statistics and performance metrics.
    """
    try:
        from app.services.cache import trading_cache
        stats = trading_cache.get_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/account/balance")
def get_account_balance():
    """
    Отримує реальний баланс акаунту з Binance
    """
    try:
        from app.services.binance_api import BinanceAPI
        api = BinanceAPI()
        balance_info = api.get_account_balance()
        
        if balance_info:
            return {
                "success": True,
                "account_type": balance_info["account_type"],
                "total_assets": balance_info["total_assets"],
                "balances": balance_info["balances"],
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "Не вдалося отримати баланс акаунту"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/account/usdt-balance")
def get_usdt_balance():
    """
    Отримує баланс в USDT
    """
    try:
        from app.services.binance_api import BinanceAPI
        api = BinanceAPI()
        usdt_balance = api.get_usdt_balance()
        
        return {
            "success": True,
            "usdt_balance": usdt_balance,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/cache/clear")
def clear_cache(request: CacheClearRequest = Body(None)):
    """
    Clear all cached data.
    """
    try:
        from app.services.cache import trading_cache
        trading_cache.clear()
        return {
            "success": True,
            "message": "Cache cleared successfully",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# =============================================================================
# РИЗИК-МЕНЕДЖМЕНТ API
# =============================================================================

@app.get("/risk/metrics")
def get_risk_metrics():
    """
    Отримує поточні метрики ризику
    """
    try:
        risk_manager = get_risk_manager()
        metrics = risk_manager.get_risk_metrics()
        return {
            "success": True,
            "metrics": {
                "total_exposure": metrics.total_exposure,
                "max_drawdown": metrics.max_drawdown,
                "win_rate": metrics.win_rate,
                "avg_win": metrics.avg_win,
                "avg_loss": metrics.avg_loss,
                "sharpe_ratio": metrics.sharpe_ratio,
                "daily_pnl": metrics.daily_pnl,
                "volatility": metrics.volatility
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/risk/validate-trade")
def validate_trade(symbol: str, side: str, quantity: float, price: float, account_balance: float = 10000.0):
    """
    Валідує угоду на відповідність правилам ризик-менеджменту
    """
    try:
        risk_manager = get_risk_manager()
        is_valid, reason = risk_manager.validate_trade(symbol, side, quantity, price, account_balance)
        
        return {
            "success": True,
            "is_valid": is_valid,
            "reason": reason,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "position_value": quantity * price
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/risk/position-size/{symbol}")
def calculate_position_size(symbol: str, entry_price: float, account_balance: float = 10000.0):
    """
    Розраховує безпечний розмір позиції
    """
    try:
        risk_manager = get_risk_manager()
        quantity = risk_manager.calculate_position_size(symbol, entry_price, account_balance)
        
        return {
            "success": True,
            "symbol": symbol,
            "entry_price": entry_price,
            "quantity": quantity,
            "position_value": quantity * entry_price,
            "account_balance": account_balance
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/risk/stop-loss/{symbol}")
def get_stop_loss_price(symbol: str, entry_price: float, side: str):
    """
    Розраховує ціну Stop Loss
    """
    try:
        risk_manager = get_risk_manager()
        stop_loss_price = risk_manager.calculate_stop_loss_price(symbol, entry_price, side)
        
        return {
            "success": True,
            "symbol": symbol,
            "entry_price": entry_price,
            "side": side,
            "stop_loss_price": stop_loss_price,
            "stop_loss_percent": risk_manager.config.stop_loss_percent
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/risk/take-profit/{symbol}")
def get_take_profit_price(symbol: str, entry_price: float, side: str):
    """
    Розраховує ціну Take Profit
    """
    try:
        risk_manager = get_risk_manager()
        take_profit_price = risk_manager.calculate_take_profit_price(symbol, entry_price, side)
        
        return {
            "success": True,
            "symbol": symbol,
            "entry_price": entry_price,
            "side": side,
            "take_profit_price": take_profit_price,
            "take_profit_percent": risk_manager.config.take_profit_percent
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# =============================================================================
# ТОРГОВИЙ ДВИГУН API
# =============================================================================

@app.post("/trading/start")
def start_trading_engine(request: TradingStartRequest = Body(None)):
    """
    Запускає торговий двигун
    """
    try:
        trading_engine = get_trading_engine()
        import asyncio
        
        # Якщо trading_pairs не передано, використовуємо значення за замовчуванням
        if request is None:
            trading_pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        else:
            trading_pairs = request.trading_pairs or ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        # Запускаємо в окремому потоці
        def run_engine():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(trading_engine.start(trading_pairs))
        
        threading.Thread(target=run_engine, daemon=True).start()
        
        return {
            "success": True,
            "message": "Торговий двигун запущений",
            "trading_pairs": trading_pairs
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/trading/stop")
def stop_trading_engine(request: TradingStopRequest = Body(None)):
    """
    Зупиняє торговий двигун
    """
    try:
        trading_engine = get_trading_engine()
        import asyncio
        
        def stop_engine():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(trading_engine.stop())
        
        threading.Thread(target=stop_engine, daemon=True).start()
        
        return {
            "success": True,
            "message": "Торговий двигун зупинений"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/trading/status")
def get_trading_status():
    """
    Отримує статус торгового двигуна
    """
    try:
        trading_engine = get_trading_engine()
        return {
            "success": True,
            "is_running": trading_engine.is_running,
            "trading_pairs": trading_engine.trading_pairs,
            "active_orders": len(trading_engine.active_orders),
            "account_balance": trading_engine.account_balance
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# =============================================================================
# МОНІТОРИНГ API
# =============================================================================

@app.get("/monitoring/status")
def get_monitoring_status():
    """
    Отримує статус системи моніторингу
    """
    try:
        monitoring_service = get_monitoring_service()
        status = monitoring_service.get_system_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/monitoring/alerts")
def get_alerts(hours: int = 24):
    """
    Отримує історію сповіщень
    """
    try:
        monitoring_service = get_monitoring_service()
        alerts = monitoring_service.get_alert_history(hours)
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/monitoring/start")
def start_monitoring(request: MonitoringStartRequest = Body(None)):
    """
    Запускає моніторинг
    """
    try:
        monitoring_service = get_monitoring_service()
        import asyncio
        
        def run_monitoring():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(monitoring_service.start_monitoring())
        
        threading.Thread(target=run_monitoring, daemon=True).start()
        
        return {
            "success": True,
            "message": "Моніторинг запущений"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/monitoring/stop")
def stop_monitoring(request: MonitoringStopRequest = Body(None)):
    """
    Зупиняє моніторинг
    """
    try:
        monitoring_service = get_monitoring_service()
        import asyncio
        
        def stop_monitoring_service():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(monitoring_service.stop_monitoring())
        
        threading.Thread(target=stop_monitoring_service, daemon=True).start()
        
        return {
            "success": True,
            "message": "Моніторинг зупинений"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# =============================================================================
# АНАЛІТИКА API
# =============================================================================

@app.get("/analytics/quick-stats")
def get_quick_stats():
    """
    Отримує швидку статистику за останні 24 години
    """
    try:
        analytics_service = get_analytics_service()
        stats = analytics_service.get_quick_stats()
        
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/analytics/performance-report")
def get_performance_report(days: int = 30):
    """
    Генерує звіт про продуктивність за вказаний період
    """
    try:
        analytics_service = get_analytics_service()
        report = analytics_service.generate_performance_report(days)
        
        return {
            "success": True,
            "report": {
                "period": report.period,
                "start_date": report.start_date.isoformat(),
                "end_date": report.end_date.isoformat(),
                "metrics": {
                    "total_trades": report.metrics.total_trades,
                    "winning_trades": report.metrics.winning_trades,
                    "losing_trades": report.metrics.losing_trades,
                    "win_rate": report.metrics.win_rate,
                    "total_profit": report.metrics.total_profit,
                    "total_loss": report.metrics.total_loss,
                    "net_profit": report.metrics.net_profit,
                    "avg_win": report.metrics.avg_win,
                    "avg_loss": report.metrics.avg_loss,
                    "profit_factor": report.metrics.profit_factor,
                    "max_drawdown": report.metrics.max_drawdown,
                    "sharpe_ratio": report.metrics.sharpe_ratio,
                    "avg_trade_duration": report.metrics.avg_trade_duration,
                    "best_trade": report.metrics.best_trade,
                    "worst_trade": report.metrics.worst_trade
                },
                "top_symbols": report.top_symbols,
                "daily_returns": report.daily_returns,
                "risk_metrics": report.risk_metrics,
                "recommendations": report.recommendations
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/analytics/export-report")
def export_performance_report(days: int = 30):
    """
    Експортує звіт про продуктивність у JSON формат
    """
    try:
        analytics_service = get_analytics_service()
        report = analytics_service.generate_performance_report(days)
        json_report = analytics_service.export_report_to_json(report)
        
        return {
            "success": True,
            "report_json": json_report,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.on_event("startup")
def launch_telegram_bot():
    """
    Launch the Telegram bot in a separate daemon thread when the API starts.
    """
    threading.Thread(target=start_telegram_bot, daemon=True).start()


