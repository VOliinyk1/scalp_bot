# Система Ризик-Менеджменту для Торгового Бота

## Огляд

Ця система ризик-менеджменту забезпечує комплексний контроль ризиків для автоматичного торгового бота на Binance. Вона включає в себе:

- **Автоматичну валідацію угод** перед виконанням
- **Розрахунок безпечних розмірів позицій** на основі ризику
- **Stop Loss та Take Profit** автоматичне управління
- **Моніторинг ризиків в реальному часі**
- **Сповіщення про критичні ситуації**
- **Гнучкі налаштування** для різних профілів ризику

## Основні Компоненти

### 1. RiskManager (`app/services/risk_management.py`)

Центральний компонент системи ризик-менеджменту.

**Основні функції:**

- Валідація угод на відповідність правилам
- Розрахунок розмірів позицій
- Управління Stop Loss та Take Profit
- Моніторинг позицій в реальному часі

**Ключові методи:**

```python
# Валідація угоди
is_valid, reason = risk_manager.validate_trade(symbol, side, quantity, price, balance)

# Розрахунок розміру позиції
quantity = risk_manager.calculate_position_size(symbol, entry_price, account_balance)

# Перевірка Stop Loss / Take Profit
exit_signals = risk_manager.check_stop_loss_take_profit(symbol, current_price)
```

### 2. TradingEngine (`app/services/trading_engine.py`)

Автоматичний торговий двигун з інтеграцією ризик-менеджменту.

**Основні функції:**

- Автоматичне виконання угод
- Моніторинг цін в реальному часі
- Обробка торгових сигналів
- Управління ордерами

**Запуск:**

```python
# Запуск торгового двигуна
await trading_engine.start(["BTCUSDT", "ETHUSDT", "BNBUSDT"])

# Зупинка
await trading_engine.stop()
```

### 3. MonitoringService (`app/services/monitoring.py`)

Система моніторингу та сповіщень.

**Основні функції:**

- Моніторинг ризиків в реальному часі
- Перевірка здоров'я системи
- Відправка сповіщень через Telegram
- Збір метрик продуктивності

## Конфігурація Ризик-Менеджменту

### Профілі Ризику

#### 1. Консервативний (Conservative)

- **Розмір позиції:** 500 USDT
- **Загальна експозиція:** 2,500 USDT
- **Денний збиток:** 100 USDT
- **Просадка:** 5%
- **Stop Loss:** 3%
- **Take Profit:** 6%

#### 2. Базовий (Default)

- **Розмір позиції:** 1,000 USDT
- **Загальна експозиція:** 5,000 USDT
- **Денний збиток:** 200 USDT
- **Просадка:** 10%
- **Stop Loss:** 5%
- **Take Profit:** 10%

#### 3. Агресивний (Aggressive)

- **Розмір позиції:** 2,000 USDT
- **Загальна експозиція:** 10,000 USDT
- **Денний збиток:** 400 USDT
- **Просадка:** 15%
- **Stop Loss:** 7%
- **Take Profit:** 15%

### Налаштування для Різних Активів

```python
# Специфічні налаштування для BTC
BTCUSDT_CONFIG = {
    "max_position_size_usdt": 1500.0,
    "max_volatility_threshold": 0.06,
    "min_liquidity_usdt": 5000000.0
}

# Специфічні налаштування для ETH
ETHUSDT_CONFIG = {
    "max_position_size_usdt": 1200.0,
    "max_volatility_threshold": 0.07,
    "min_liquidity_usdt": 3000000.0
}
```

### Налаштування для Часових Інтервалів

```python
# Короткострокові угоди (1m)
TIMEFRAME_1M = {
    "max_holding_time_hours": 1,
    "min_time_between_trades_minutes": 5,
    "stop_loss_percent": 2.0,
    "take_profit_percent": 3.0
}

# Довгострокові угоди (4h)
TIMEFRAME_4H = {
    "max_holding_time_hours": 72,
    "min_time_between_trades_minutes": 120,
    "stop_loss_percent": 7.0,
    "take_profit_percent": 15.0
}
```

## API Ендпоінти

### Ризик-Менеджмент

#### Отримання метрик ризику

```http
GET /risk/metrics
```

**Відповідь:**

```json
{
  "success": true,
  "metrics": {
    "total_exposure": 2500.0,
    "max_drawdown": 5.2,
    "win_rate": 0.65,
    "avg_win": 120.0,
    "avg_loss": -80.0,
    "sharpe_ratio": 1.2,
    "daily_pnl": 150.0,
    "volatility": 0.04
  }
}
```

#### Валідація угоди

```http
POST /risk/validate-trade
Content-Type: application/json

{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "quantity": 0.01,
  "price": 45000.0,
  "account_balance": 10000.0
}
```

#### Розрахунок розміру позиції

```http
GET /risk/position-size/BTCUSDT?entry_price=45000&account_balance=10000
```

#### Розрахунок Stop Loss

```http
GET /risk/stop-loss/BTCUSDT?entry_price=45000&side=BUY
```

#### Розрахунок Take Profit

```http
GET /risk/take-profit/BTCUSDT?entry_price=45000&side=BUY
```

### Торговий Двигун

#### Запуск торгового двигуна

```http
POST /trading/start
Content-Type: application/json

{
  "trading_pairs": ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
}
```

#### Статус торгового двигуна

```http
GET /trading/status
```

#### Зупинка торгового двигуна

```http
POST /trading/stop
```

### Моніторинг

#### Статус системи

```http
GET /monitoring/status
```

#### Історія сповіщень

```http
GET /monitoring/alerts?hours=24
```

#### Запуск моніторингу

```http
POST /monitoring/start
```

## Приклади Використання

### 1. Налаштування консервативного профілю

```python
from app.risk_config import get_risk_config
from app.services.risk_management import RiskManager

# Отримуємо консервативну конфігурацію
config = get_risk_config(profile="conservative", asset="BTCUSDT", timeframe="1h")

# Створюємо менеджер ризиків
risk_manager = RiskManager(config)
```

### 2. Валідація угоди

```python
# Перевіряємо угоду перед виконанням
is_valid, reason = risk_manager.validate_trade(
    symbol="BTCUSDT",
    side="BUY",
    quantity=0.01,
    price=45000.0,
    account_balance=10000.0
)

if is_valid:
    print("Угода дозволена")
else:
    print(f"Угода відхилена: {reason}")
```

### 3. Розрахунок розміру позиції

```python
# Розраховуємо безпечний розмір позиції
quantity = risk_manager.calculate_position_size(
    symbol="BTCUSDT",
    entry_price=45000.0,
    account_balance=10000.0
)

print(f"Рекомендований розмір позиції: {quantity:.8f} BTC")
```

### 4. Автоматичне управління позиціями

```python
# Перевіряємо Stop Loss / Take Profit
current_price = 44000.0  # Поточна ціна
exit_signals = risk_manager.check_stop_loss_take_profit("BTCUSDT", current_price)

for signal in exit_signals:
    print(f"Сигнал виходу: {signal['type']} - {signal['reason']}")
```

### 5. Запуск повної системи

```python
import asyncio
from app.services.trading_engine import get_trading_engine
from app.services.monitoring import get_monitoring_service

async def main():
    # Запускаємо торговий двигун
    trading_engine = get_trading_engine()
    await trading_engine.start(["BTCUSDT", "ETHUSDT"])

    # Запускаємо моніторинг
    monitoring_service = get_monitoring_service()
    await monitoring_service.start_monitoring()

    # Тримаємо систему запущеною
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await trading_engine.stop()
        await monitoring_service.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

## Метрики та Аналітика

### Ключові Показники

1. **Загальна експозиція** - сума всіх відкритих позицій
2. **Максимальна просадка** - найбільша втрата від піку
3. **Win Rate** - відсоток прибуткових угод
4. **Середній прибуток/збиток** - статистика угод
5. **Коефіцієнт Шарпа** - співвідношення прибутку до ризику
6. **Волатильність портфеля** - мінливість прибутків

### Рівні Ризику

- **🟢 LOW** - Низький ризик, нормальна робота
- **🟡 MEDIUM** - Середній ризик, увага
- **🟠 HIGH** - Високий ризик, обережність
- **🔴 CRITICAL** - Критичний ризик, негайна дія

## Безпека та Обмеження

### Валідація Вхідних Даних

Система перевіряє:

- Коректність символів торгових пар
- Валідність цін та кількостей
- Достатність балансу
- Відповідність лімітам

### Захист від Помилок

- Автоматичне скасування невиконаних ордерів
- Обмеження частоти угод
- Перевірка ліквідності
- Моніторинг стану API

### Резервне Копіювання

- Збереження всіх угод в базі даних
- Логування всіх дій
- Історія змін конфігурації
- Автоматичне відновлення після збоїв

## Налаштування Telegram Сповіщень

1. Створіть бота через @BotFather
2. Отримайте токен
3. Додайте токен в `.env` файл:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

4. Надішліть повідомлення боту для отримання chat_id
5. Оновіть chat_id в коді моніторингу

## Моніторинг та Діагностика

### Логи

Всі дії системи логуються з різними рівнями:

- **INFO** - звичайні операції
- **WARNING** - попередження про ризики
- **ERROR** - помилки та збої

### Метрики

Система збирає метрики:

- Кількість угод
- Прибутковість
- Час відгуку API
- Використання пам'яті
- Статистика кешу

### Сповіщення

Автоматичні сповіщення про:

- Критичні рівні ризику
- Збої системи
- Важливі події
- Щоденні звіти

## Розширення та Кастомізація

### Додавання Нових Правил

```python
class CustomRiskRule:
    def validate(self, trade_data):
        # Ваша логіка валідації
        pass

# Додаємо правило до менеджера ризиків
risk_manager.add_custom_rule(CustomRiskRule())
```

### Нові Типи Сповіщень

```python
class CustomAlert:
    def send(self, message):
        # Ваша логіка відправки
        pass

# Додаємо до моніторингу
monitoring_service.add_alert_type(CustomAlert())
```

### Інтеграція з Іншими Біржами

Система легко розширюється для підтримки інших бірж через абстракцію API.

## Підтримка та Обслуговування

### Регулярні Перевірки

- Щоденний аналіз метрик
- Тижневий огляд конфігурації
- Місячний звіт про продуктивність

### Оновлення

- Регулярні оновлення правил ризик-менеджменту
- Покращення алгоритмів
- Додавання нових функцій

### Підтримка

- Документація API
- Приклади використання
- Технічна підтримка

---

**Важливо:** Ця система призначена для допомоги в управлінні ризиками, але не гарантує прибутковість. Завжди тестуйте на демо-рахунках перед використанням на реальних коштах.
