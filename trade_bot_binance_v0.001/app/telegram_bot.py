# app/telegram_bot.py

import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from dotenv import load_dotenv

from app.ai_signals import detect_signal

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    await message.reply("👋 Вітаю! Я торговий бот. Напиши /signal ETHUSDT щоб отримати сигнал.")

@dp.message_handler(commands=["signal"])
async def signal_cmd(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("⚠️ Формат: /signal SYMBOL (наприклад: /signal BTCUSDT)")
            return

        symbol = parts[1].upper()
        result = detect_signal(symbol)

        if result["signal"] == "ERROR":
            await message.reply(f"❌ Помилка: {result['error']}")
        else:
            msg = (
                f"📊 <b>{symbol}</b>\n"
                f"💡 Сигнал: <b>{result['signal']}</b>\n"
                f"📈 RSI: {result['rsi']}\n"
                f"📊 MACD: {result['macd']} / {result['macd_signal']}\n"
                f"🔍 Причини:\n"
                + "\n".join([f"• {r}" for r in result["reasons"]]) +
                f"\n\n🧠 Confidence: {int(result['confidence'] * 100)}%"
            )
            await message.reply(msg, parse_mode=ParseMode.HTML)

    except Exception as e:
        await message.reply(f"⚠️ Внутрішня помилка: {str(e)}")

def start_telegram_bot():
    executor.start_polling(dp, skip_updates=True)
