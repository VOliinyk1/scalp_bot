# Trade Bot — Smart Money Trading Bot

Торговий бот для Binance з AI сигналами та Smart Money аналізом.

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

- `GET /` - Перевірка роботи сервера
- `GET /signal/{symbol}` - AI сигнал для символу
- `GET /smart_money/{symbol}` - Smart Money аналіз
- `GET /signals/latest/{symbol}` - Останній сигнал з БД
- `GET /cache/stats` - Статистика кешу
- `POST /cache/clear` - Очистити кеш

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
└── services/
    ├── ai_signals.py    # AI сигнальна система
    ├── smart_money.py   # Smart Money аналіз
    ├── binance_api.py   # Binance API
    ├── new_sentiment.py # Сентимент аналіз
    └── cache.py         # Система кешування
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
