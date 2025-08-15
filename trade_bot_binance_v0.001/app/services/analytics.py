# app/services/analytics.py
"""
Модуль аналітики для торгового бота
Генерує звіти та аналізує продуктивність торгівлі
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import get_db, SessionLocal
from app.models import Order, Trade, Signal
from app.services.risk_management import get_risk_manager

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradingMetrics:
    """Метрики торгівлі"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_loss: float
    net_profit: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    avg_trade_duration: float
    best_trade: float
    worst_trade: float

@dataclass
class PerformanceReport:
    """Звіт про продуктивність"""
    period: str
    start_date: datetime
    end_date: datetime
    metrics: TradingMetrics
    top_symbols: List[Dict]
    daily_returns: List[Dict]
    risk_metrics: Dict
    recommendations: List[str]

class AnalyticsService:
    """Сервіс аналітики"""
    
    def __init__(self):
        self.risk_manager = get_risk_manager()
    
    def generate_performance_report(self, days: int = 30) -> PerformanceReport:
        """
        Генерує звіт про продуктивність за вказаний період
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            with SessionLocal() as db:
                # Отримуємо всі угоди за період
                trades = db.query(Trade).filter(
                    and_(
                        Trade.created_at >= start_date,
                        Trade.created_at <= end_date
                    )
                ).all()
                
                if not trades:
                    return self._create_empty_report(start_date, end_date)
                
                # Розраховуємо метрики
                metrics = self._calculate_trading_metrics(trades)
                
                # Аналізуємо топ символи
                top_symbols = self._analyze_top_symbols(db, start_date, end_date)
                
                # Розраховуємо денні прибутки
                daily_returns = self._calculate_daily_returns(trades)
                
                # Отримуємо метрики ризику
                risk_metrics = self.risk_manager.get_risk_metrics()
                
                # Генеруємо рекомендації
                recommendations = self._generate_recommendations(metrics, risk_metrics)
                
                return PerformanceReport(
                    period=f"Останні {days} днів",
                    start_date=start_date,
                    end_date=end_date,
                    metrics=metrics,
                    top_symbols=top_symbols,
                    daily_returns=daily_returns,
                    risk_metrics=asdict(risk_metrics),
                    recommendations=recommendations
                )
                
        except Exception as e:
            logger.error(f"Помилка генерації звіту: {e}")
            return self._create_empty_report(start_date, end_date)
    
    def _calculate_trading_metrics(self, trades: List[Trade]) -> TradingMetrics:
        """Розраховує метрики торгівлі"""
        if not trades:
            return TradingMetrics(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, total_profit=0.0, total_loss=0.0,
                net_profit=0.0, avg_win=0.0, avg_loss=0.0,
                profit_factor=0.0, max_drawdown=0.0, sharpe_ratio=0.0,
                avg_trade_duration=0.0, best_trade=0.0, worst_trade=0.0
            )
        
        # Розділяємо угоди на прибуткові та збиткові
        profits = [t.realized_pnl for t in trades if t.realized_pnl > 0]
        losses = [t.realized_pnl for t in trades if t.realized_pnl < 0]
        
        total_trades = len(trades)
        winning_trades = len(profits)
        losing_trades = len(losses)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        total_profit = sum(profits) if profits else 0.0
        total_loss = abs(sum(losses)) if losses else 0.0
        net_profit = total_profit - total_loss
        
        avg_win = total_profit / winning_trades if winning_trades > 0 else 0.0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0.0
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Розраховуємо максимальну просадку
        cumulative_pnl = []
        running_total = 0
        for trade in trades:
            running_total += trade.realized_pnl
            cumulative_pnl.append(running_total)
        
        max_drawdown = self._calculate_max_drawdown(cumulative_pnl)
        
        # Розраховуємо коефіцієнт Шарпа (спрощено)
        returns = [t.realized_pnl for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0.0
        
        # Середня тривалість угоди
        durations = []
        for trade in trades:
            if trade.closed_at and trade.created_at:
                duration = (trade.closed_at - trade.created_at).total_seconds() / 3600  # години
                durations.append(duration)
        
        avg_trade_duration = np.mean(durations) if durations else 0.0
        
        # Найкраща та найгірша угода
        best_trade = max(profits) if profits else 0.0
        worst_trade = min(losses) if losses else 0.0
        
        return TradingMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            avg_trade_duration=avg_trade_duration,
            best_trade=best_trade,
            worst_trade=worst_trade
        )
    
    def _calculate_max_drawdown(self, cumulative_pnl: List[float]) -> float:
        """Розраховує максимальну просадку"""
        if not cumulative_pnl:
            return 0.0
        
        peak = cumulative_pnl[0]
        max_dd = 0.0
        
        for value in cumulative_pnl:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        
        return max_dd * 100  # Повертаємо у відсотках
    
    def _analyze_top_symbols(self, db: Session, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Аналізує топ символи за продуктивністю"""
        try:
            # Групуємо угоди за символами
            symbol_stats = db.query(
                Trade.symbol,
                func.count(Trade.id).label('total_trades'),
                func.sum(Trade.realized_pnl).label('total_pnl'),
                func.avg(Trade.realized_pnl).label('avg_pnl')
            ).filter(
                and_(
                    Trade.created_at >= start_date,
                    Trade.created_at <= end_date
                )
            ).group_by(Trade.symbol).all()
            
            # Сортуємо за загальним P&L
            symbol_stats = sorted(symbol_stats, key=lambda x: x.total_pnl, reverse=True)
            
            return [
                {
                    "symbol": stat.symbol,
                    "total_trades": stat.total_trades,
                    "total_pnl": float(stat.total_pnl),
                    "avg_pnl": float(stat.avg_pnl)
                }
                for stat in symbol_stats[:10]  # Топ 10
            ]
            
        except Exception as e:
            logger.error(f"Помилка аналізу символів: {e}")
            return []
    
    def _calculate_daily_returns(self, trades: List[Trade]) -> List[Dict]:
        """Розраховує денні прибутки"""
        try:
            # Групуємо угоди за днями
            daily_pnl = {}
            for trade in trades:
                date_key = trade.created_at.date().isoformat()
                if date_key not in daily_pnl:
                    daily_pnl[date_key] = 0.0
                daily_pnl[date_key] += trade.realized_pnl
            
            # Конвертуємо в список
            return [
                {
                    "date": date,
                    "pnl": pnl,
                    "cumulative_pnl": sum(list(daily_pnl.values())[:i+1])
                }
                for i, (date, pnl) in enumerate(daily_pnl.items())
            ]
            
        except Exception as e:
            logger.error(f"Помилка розрахунку денних прибутків: {e}")
            return []
    
    def _generate_recommendations(self, metrics: TradingMetrics, risk_metrics: Dict) -> List[str]:
        """Генерує рекомендації на основі метрик"""
        recommendations = []
        
        # Аналіз відсотка виграшів
        if metrics.win_rate < 0.4:
            recommendations.append("Низький відсоток виграшів. Розгляньте покращення стратегії входу.")
        elif metrics.win_rate > 0.7:
            recommendations.append("Високий відсоток виграшів. Можливо, можна збільшити розмір позицій.")
        
        # Аналіз profit factor
        if metrics.profit_factor < 1.5:
            recommendations.append("Низький profit factor. Покращіть співвідношення ризик/прибуток.")
        
        # Аналіз максимальної просадки
        if metrics.max_drawdown > 20:
            recommendations.append("Висока максимальна просадка. Зменшіть розмір позицій або покращіть управління ризиками.")
        
        # Аналіз коефіцієнта Шарпа
        if metrics.sharpe_ratio < 1.0:
            recommendations.append("Низький коефіцієнт Шарпа. Покращіть стабільність прибутків.")
        
        # Аналіз середньої тривалості угоди
        if metrics.avg_trade_duration < 1:
            recommendations.append("Дуже короткі угоди. Розгляньте довгострокові стратегії.")
        elif metrics.avg_trade_duration > 24:
            recommendations.append("Дуже довгі угоди. Розгляньте короткострокові стратегії.")
        
        # Загальні рекомендації
        if not recommendations:
            recommendations.append("Відмінна продуктивність! Продовжуйте поточну стратегію.")
        
        return recommendations
    
    def _create_empty_report(self, start_date: datetime, end_date: datetime) -> PerformanceReport:
        """Створює порожній звіт"""
        empty_metrics = TradingMetrics(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0.0, total_profit=0.0, total_loss=0.0,
            net_profit=0.0, avg_win=0.0, avg_loss=0.0,
            profit_factor=0.0, max_drawdown=0.0, sharpe_ratio=0.0,
            avg_trade_duration=0.0, best_trade=0.0, worst_trade=0.0
        )
        
        return PerformanceReport(
            period="Немає даних",
            start_date=start_date,
            end_date=end_date,
            metrics=empty_metrics,
            top_symbols=[],
            daily_returns=[],
            risk_metrics={},
            recommendations=["Немає даних для аналізу"]
        )
    
    def export_report_to_json(self, report: PerformanceReport) -> str:
        """Експортує звіт у JSON формат"""
        try:
            report_dict = {
                "period": report.period,
                "start_date": report.start_date.isoformat(),
                "end_date": report.end_date.isoformat(),
                "metrics": asdict(report.metrics),
                "top_symbols": report.top_symbols,
                "daily_returns": report.daily_returns,
                "risk_metrics": report.risk_metrics,
                "recommendations": report.recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return json.dumps(report_dict, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Помилка експорту звіту: {e}")
            return "{}"
    
    def get_quick_stats(self) -> Dict[str, Any]:
        """Отримує швидку статистику за останні 24 години"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=24)
            
            with SessionLocal() as db:
                trades = db.query(Trade).filter(
                    and_(
                        Trade.created_at >= start_date,
                        Trade.created_at <= end_date
                    )
                ).all()
                
                if not trades:
                    return {
                        "period": "24 години",
                        "total_trades": 0,
                        "net_pnl": 0.0,
                        "win_rate": 0.0,
                        "best_symbol": None
                    }
                
                # Розраховуємо базові метрики
                total_trades = len(trades)
                net_pnl = sum(t.realized_pnl for t in trades)
                winning_trades = len([t for t in trades if t.realized_pnl > 0])
                win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
                
                # Знаходимо найкращий символ
                symbol_pnl = {}
                for trade in trades:
                    if trade.symbol not in symbol_pnl:
                        symbol_pnl[trade.symbol] = 0.0
                    symbol_pnl[trade.symbol] += trade.realized_pnl
                
                best_symbol = max(symbol_pnl.items(), key=lambda x: x[1])[0] if symbol_pnl else None
                
                return {
                    "period": "24 години",
                    "total_trades": total_trades,
                    "net_pnl": net_pnl,
                    "win_rate": win_rate,
                    "best_symbol": best_symbol
                }
                
        except Exception as e:
            logger.error(f"Помилка отримання швидкої статистики: {e}")
            return {
                "period": "24 години",
                "total_trades": 0,
                "net_pnl": 0.0,
                "win_rate": 0.0,
                "best_symbol": None,
                "error": str(e)
            }

# Глобальний екземпляр сервісу
_analytics_service = None

def get_analytics_service() -> AnalyticsService:
    """Отримує глобальний екземпляр сервісу аналітики"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
