# Trade Bot — Smart Money Trading Bot з Системою Ризик-Менеджменту

Торговий бот для Binance з AI сигналами, Smart Money аналізом та комплексною системою ризик-менеджменту в реальному часі.

## 🚀 Нові Можливості

### Система Ризик-Менеджменту

- **Автоматична валідація угод** перед виконанням
- **Розрахунок безпечних розмірів позицій** на основі ризику
- **Stop Loss та Take Profit** автоматичне управління
- **Моніторинг ризиків в реальному часі**
- **Сповіщення про критичні ситуації**
- **Гнучкі налаштування** для різних профілів ризику

### Торговий Двигун

- **Автоматичне виконання угод** з дотриманням правил ризик-менеджменту
- **Моніторинг цін в реальному часі**
- **Обробка торгових сигналів**
- **Управління ордерами**

### Система Моніторингу

- **Відстеження стану системи**
- **Telegram сповіщення**
- **Метрики продуктивності**
- **Історія сповіщень**

## 🚀 Швидкий старт

### 1. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 2. Налаштування змінних середовища

Створіть файл `.env` з наступними змінними:

```env
# Binance API
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# Database
DATABASE_URL=sqlite:///./trading_bot.db

# OpenAI API (для сентимент аналізу)
OPENAI_API_KEY=your_openai_api_key_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
FASTAPI_URL=http://localhost:8000
```

### 3. Ініціалізація бази даних

```bash
python app/init_db.py
```

### 4. Запуск сервера

```bash
# Варіант 1: Прямий запуск
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Варіант 2: Через скрипт запуску
python app/run.py
```

## 🤖 Telegram Bot Команди

- `/start` або `/help` - Показати всі команди
- `/ai_signal SYMBOL` - Повний AI аналіз (наприклад: `/ai_signal BTCUSDT`)
- `/smart_money SYMBOL` - Smart Money аналіз (наприклад: `/smart_money ETHUSDT`)
- `/last SYMBOL` - Останній збережений сигнал
- `/cache_stats` - Статистика кешу
- `/cache_clear` - Очистити кеш

## 📊 API Ендпоінти

### Основні API

- `GET /` - Перевірка роботи сервера
- `GET /signal/{symbol}` - AI сигнал для символу
- `GET /smart_money/{symbol}` - Smart Money аналіз
- `GET /signals/latest/{symbol}` - Останній сигнал з БД
- `GET /cache/stats` - Статистика кешу
- `POST /cache/clear` - Очистити кеш

### Ризик-Менеджмент API

- `GET /risk/metrics` - Отримання метрик ризику
- `POST /risk/validate-trade` - Валідація угоди
- `GET /risk/position-size/{symbol}` - Розрахунок розміру позиції
- `GET /risk/stop-loss/{symbol}` - Розрахунок Stop Loss
- `GET /risk/take-profit/{symbol}` - Розрахунок Take Profit

### Торговий Двигун API

- `GET /trading/status` - Статус торгового двигуна
- `POST /trading/start` - Запуск торгового двигуна
- `POST /trading/stop` - Зупинка торгового двигуна

### Моніторинг API

- `GET /monitoring/status` - Статус системи моніторингу
- `GET /monitoring/alerts` - Історія сповіщень
- `POST /monitoring/start` - Запуск моніторингу
- `POST /monitoring/stop` - Зупинка моніторингу

## 🧠 Smart Money Модуль

Smart Money модуль включає:

- Машинне навчання (LogisticRegression)
- Технічні індикатори (RSI, MACD, ADX, ATR)
- Аналіз дисбалансу ордербука
- Сентимент аналіз новин
- Автоматичне перетренування моделі

## ⚡ Система кешування

Система кешування покращує продуктивність:

- **Кешування OHLCV даних** - зменшує запити до Binance API
- **Кешування Smart Money сигналів** - прискорює відповіді
- **Автоматичне очищення** - видаляє застарілі дані
- **Статистика продуктивності** - моніторинг ефективності кешу
- **Налаштовувані TTL** - різний час життя для різних типів даних

## 🧪 Тестування

```bash
# Тестування Smart Money модуля
python app/test_smart_money.py

# Тестування системи кешування
python app/test_cache.py

# Тестування системи ризик-менеджменту
python test_risk_management.py

# Тестування API
python api_examples.py
```

## 📁 Структура проекту

```
app/
├── main.py              # FastAPI сервер
├── config.py            # Конфігурація
├── database.py          # База даних
├── models.py            # Моделі БД
├── telegram_bot.py      # Telegram бот
├── run.py               # Скрипт запуску
├── test_smart_money.py  # Тестування Smart Money
├── risk_config.py       # Конфігурація ризик-менеджменту
└── services/
    ├── ai_signals.py    # AI сигнальна система
    ├── smart_money.py   # Smart Money аналіз
    ├── binance_api.py   # Binance API
    ├── new_sentiment.py # Сентимент аналіз
    ├── cache.py         # Система кешування
    ├── risk_management.py # Система ризик-менеджменту
    ├── trading_engine.py  # Торговий двигун
    └── monitoring.py      # Система моніторингу

# Документація та тести
├── RISK_MANAGEMENT_README.md # Документація ризик-менеджменту
├── test_risk_management.py   # Тестування системи ризик-менеджменту
└── api_examples.py           # Приклади використання API
```

## 🔧 Налаштування

### Smart Money параметри (опціонально)

```env
SM_SYMBOL=BTCUSDT
SM_TIMEFRAME=5m
SM_HORIZON_BARS=12
SM_POS_TH=0.002
SM_NEG_TH=-0.002
SM_RETRAIN_HOURS=6
```

### Ваги сигналів

```env
SIGNAL_WEIGHTS={"tech":0.5,"smart":0.25,"gpt":0.25}
```

## 🎯 Доступні пари

BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, DOTUSDT та інші пари з Binance.

## 📚 Документація

- [Документація системи ризик-менеджменту](RISK_MANAGEMENT_README.md) - Детальний опис системи ризик-менеджменту
- [Приклади використання API](api_examples.py) - Приклади роботи з API
- [Тестування системи](test_risk_management.py) - Тести для перевірки роботи системи

## ⚠️ Важливо

**Ця система призначена для допомоги в управлінні ризиками, але не гарантує прибутковість. Завжди тестуйте на демо-рахунках перед використанням на реальних коштах.**
