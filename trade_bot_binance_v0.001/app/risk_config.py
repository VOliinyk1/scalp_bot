# app/risk_config.py
"""
Конфігурація ризик-менеджменту для торгового бота
"""

from app.services.risk_management import RiskConfig

# Базові налаштування ризик-менеджменту
DEFAULT_RISK_CONFIG = RiskConfig(
    # Ліміти на позиції
    max_position_size_usdt=1000.0,      # Максимальний розмір позиції в USDT
    max_total_exposure_usdt=5000.0,     # Максимальна загальна експозиція
    max_positions_per_symbol=1,         # Максимум позицій на символ
    
    # Ліміти на збитки
    max_daily_loss_usdt=200.0,          # Максимальний денний збиток
    max_drawdown_percent=10.0,          # Максимальна просадка в %
    stop_loss_percent=5.0,              # Stop Loss в %
    take_profit_percent=10.0,           # Take Profit в %
    
    # Ліміти на ризик
    max_risk_per_trade_percent=2.0,     # Максимальний ризик на угоду в %
    max_correlation_threshold=0.7,      # Максимальна кореляція між активами
    
    # Часові ліміти
    max_holding_time_hours=24,          # Максимальний час утримання позиції
    min_time_between_trades_minutes=30, # Мінімальний час між угодами
    
    # Волатильність
    max_volatility_threshold=0.05,      # Максимальна волатильність (5%)
    
    # Ліквідність
    min_liquidity_usdt=1000000.0        # Мінімальна ліквідність в USDT
)

# Консервативні налаштування (менший ризик)
CONSERVATIVE_RISK_CONFIG = RiskConfig(
    max_position_size_usdt=500.0,       # Менший розмір позиції
    max_total_exposure_usdt=2500.0,     # Менша експозиція
    max_positions_per_symbol=1,
    max_daily_loss_usdt=100.0,          # Менший денний збиток
    max_drawdown_percent=5.0,           # Менша просадка
    stop_loss_percent=3.0,              # Більш консервативний Stop Loss
    take_profit_percent=6.0,            # Менший Take Profit
    max_risk_per_trade_percent=1.0,     # Менший ризик на угоду
    max_correlation_threshold=0.5,      # Менша кореляція
    max_holding_time_hours=12,          # Менший час утримання
    min_time_between_trades_minutes=60, # Більший час між угодами
    max_volatility_threshold=0.03,      # Менша волатильність
    min_liquidity_usdt=2000000.0        # Більша ліквідність
)

# Агресивні налаштування (більший ризик)
AGGRESSIVE_RISK_CONFIG = RiskConfig(
    max_position_size_usdt=2000.0,      # Більший розмір позиції
    max_total_exposure_usdt=10000.0,    # Більша експозиція
    max_positions_per_symbol=2,         # Більше позицій на символ
    max_daily_loss_usdt=400.0,          # Більший денний збиток
    max_drawdown_percent=15.0,          # Більша просадка
    stop_loss_percent=7.0,              # Менш консервативний Stop Loss
    take_profit_percent=15.0,           # Більший Take Profit
    max_risk_per_trade_percent=3.0,     # Більший ризик на угоду
    max_correlation_threshold=0.8,      # Більша кореляція
    max_holding_time_hours=48,          # Більший час утримання
    min_time_between_trades_minutes=15, # Менший час між угодами
    max_volatility_threshold=0.08,      # Більша волатильність
    min_liquidity_usdt=500000.0         # Менша ліквідність
)

# Налаштування для різних типів активів
ASSET_SPECIFIC_CONFIGS = {
    "BTCUSDT": RiskConfig(
        max_position_size_usdt=1500.0,  # Більший розмір для BTC
        max_volatility_threshold=0.06,  # Більша волатильність для BTC
        min_liquidity_usdt=5000000.0    # Висока ліквідність BTC
    ),
    "ETHUSDT": RiskConfig(
        max_position_size_usdt=1200.0,  # Середній розмір для ETH
        max_volatility_threshold=0.07,  # Середня волатильність для ETH
        min_liquidity_usdt=3000000.0    # Висока ліквідність ETH
    ),
    "BNBUSDT": RiskConfig(
        max_position_size_usdt=800.0,   # Менший розмір для BNB
        max_volatility_threshold=0.08,  # Більша волатильність для BNB
        min_liquidity_usdt=2000000.0    # Середня ліквідність BNB
    )
}

# Налаштування для різних часових інтервалів
TIMEFRAME_SPECIFIC_CONFIGS = {
    "1m": RiskConfig(
        max_holding_time_hours=1,       # Короткий час утримання
        min_time_between_trades_minutes=5,  # Часті угоди
        stop_loss_percent=2.0,          # Тісний Stop Loss
        take_profit_percent=3.0         # Невеликий Take Profit
    ),
    "5m": RiskConfig(
        max_holding_time_hours=4,       # Середній час утримання
        min_time_between_trades_minutes=15, # Середня частота угод
        stop_loss_percent=3.0,          # Середній Stop Loss
        take_profit_percent=6.0         # Середній Take Profit
    ),
    "15m": RiskConfig(
        max_holding_time_hours=8,       # Довший час утримання
        min_time_between_trades_minutes=30, # Рідші угоди
        stop_loss_percent=4.0,          # Більший Stop Loss
        take_profit_percent=8.0         # Більший Take Profit
    ),
    "1h": RiskConfig(
        max_holding_time_hours=24,      # Довгий час утримання
        min_time_between_trades_minutes=60, # Рідкі угоди
        stop_loss_percent=5.0,          # Великий Stop Loss
        take_profit_percent=10.0        # Великий Take Profit
    ),
    "4h": RiskConfig(
        max_holding_time_hours=72,      # Дуже довгий час утримання
        min_time_between_trades_minutes=120, # Дуже рідкі угоди
        stop_loss_percent=7.0,          # Дуже великий Stop Loss
        take_profit_percent=15.0        # Дуже великий Take Profit
    )
}

def get_risk_config(profile: str = "default", asset: str = None, timeframe: str = None) -> RiskConfig:
    """
    Отримує конфігурацію ризик-менеджменту на основі профілю, активу та часового інтервалу
    """
    # Базова конфігурація
    if profile == "conservative":
        base_config = CONSERVATIVE_RISK_CONFIG
    elif profile == "aggressive":
        base_config = AGGRESSIVE_RISK_CONFIG
    else:
        base_config = DEFAULT_RISK_CONFIG
    
    # Застосовуємо специфічні налаштування для активу
    if asset and asset in ASSET_SPECIFIC_CONFIGS:
        asset_config = ASSET_SPECIFIC_CONFIGS[asset]
        # Об'єднуємо налаштування
        for field in base_config.__dataclass_fields__:
            asset_value = getattr(asset_config, field)
            if asset_value != getattr(RiskConfig(), field):  # Якщо значення відрізняється від за замовчуванням
                setattr(base_config, field, asset_value)
    
    # Застосовуємо специфічні налаштування для часового інтервалу
    if timeframe and timeframe in TIMEFRAME_SPECIFIC_CONFIGS:
        timeframe_config = TIMEFRAME_SPECIFIC_CONFIGS[timeframe]
        # Об'єднуємо налаштування
        for field in base_config.__dataclass_fields__:
            timeframe_value = getattr(timeframe_config, field)
            if timeframe_value != getattr(RiskConfig(), field):  # Якщо значення відрізняється від за замовчуванням
                setattr(base_config, field, timeframe_value)
    
    return base_config

def validate_risk_config(config: RiskConfig) -> tuple[bool, str]:
    """
    Валідує конфігурацію ризик-менеджменту
    """
    # Перевіряємо базові умови
    if config.max_position_size_usdt <= 0:
        return False, "Розмір позиції повинен бути більше 0"
    
    if config.max_total_exposure_usdt <= 0:
        return False, "Загальна експозиція повинна бути більше 0"
    
    if config.max_daily_loss_usdt <= 0:
        return False, "Денний збиток повинен бути більше 0"
    
    if config.max_drawdown_percent <= 0 or config.max_drawdown_percent > 100:
        return False, "Просадка повинна бути від 0 до 100%"
    
    if config.stop_loss_percent <= 0 or config.stop_loss_percent > 50:
        return False, "Stop Loss повинен бути від 0 до 50%"
    
    if config.take_profit_percent <= 0 or config.take_profit_percent > 100:
        return False, "Take Profit повинен бути від 0 до 100%"
    
    if config.max_risk_per_trade_percent <= 0 or config.max_risk_per_trade_percent > 10:
        return False, "Ризик на угоду повинен бути від 0 до 10%"
    
    if config.max_holding_time_hours <= 0:
        return False, "Час утримання повинен бути більше 0"
    
    if config.min_time_between_trades_minutes <= 0:
        return False, "Час між угодами повинен бути більше 0"
    
    if config.max_volatility_threshold <= 0 or config.max_volatility_threshold > 1:
        return False, "Волатильність повинна бути від 0 до 1"
    
    if config.min_liquidity_usdt <= 0:
        return False, "Ліквідність повинна бути більше 0"
    
    # Перевіряємо логічні умови
    if config.max_position_size_usdt > config.max_total_exposure_usdt:
        return False, "Розмір позиції не може перевищувати загальну експозицію"
    
    if config.stop_loss_percent >= config.take_profit_percent:
        return False, "Stop Loss повинен бути менше Take Profit"
    
    return True, "Конфігурація валідна"
