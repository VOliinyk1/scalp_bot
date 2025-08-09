# Trade Bot Binance v0.001

## Overview

This project is an automated trading bot for Binance, featuring:

- FastAPI backend for trading signals and bot management
- Telegram bot integration for notifications and commands
- AI-powered signal engine with multi-timeframe analysis
- PostgreSQL database for order, trade, log, and signal storage
- Dockerized deployment

## Project Structure

```
.env
docker-compose.yml
Dockerfile
requirements.txt
app/
    __init__.py
    config.py
    database.py
    init_db.py
    main.py
    models.py
    telegram_bot.py
    services/
        __init__.py
        ai_signals.py
        binance_api.py
        new_sentiment.py
        smart_money.py
        test_bot.py
```

## Setup

1. **Clone the repository**
2. **Configure environment variables** in `.env`
3. **Build and run with Docker:**
   ```sh
   docker-compose up --build
   ```
4. **Initialize the database:**
   ```sh
   docker-compose exec web python app/init_db.py
   ```

## Main Components

- **FastAPI app** ([app/main.py](app/main.py)): REST API for signals and bot management.
- **Telegram bot** ([app/telegram_bot.py](app/telegram_bot.py)): Receives commands and sends trading signals.
- **AI Signal Engine** ([app/services/ai_signals.py](app/services/ai_signals.py)): Aggregates technical, smart money, and sentiment signals.
- **Binance API wrapper** ([app/services/binance_api.py](app/services/binance_api.py)): Handles Binance trading operations.
- **Database models** ([app/models.py](app/models.py)): SQLAlchemy ORM models for orders, trades, logs, and signals.

## Usage

- Access API at `http://localhost:8000`
- Use Telegram bot for `/ai_signal SYMBOL` and `/last SYMBOL` commands

## License

MIT License

## Authors

- Your Name
