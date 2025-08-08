# app/telegram_bot.py
import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode="Markdown")
dp = Dispatcher(bot)

@dp.message_handler(commands=["start", "help"])
async def start_handler(message: types.Message):
    await message.answer("Привіт! Надішли /ai_signal <SYMBOL>, напр. /ai_signal ETHUSDT")

@dp.message_handler(commands=["ai_signal"])
async def ai_signal_handler(message: types.Message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            return await message.answer("❌ Використання: /ai_signal <SYMBOL>")

        symbol = parts[1].upper()
        response = requests.get(f"{FASTAPI_URL}/signal/{symbol}")

        if response.status_code != 200:
            return await message.answer("❌ Помилка сервера або неправильний символ")

        data = response.json()
        if data.get("final_signal") == "ERROR":
            return await message.answer(f"⚠️ Помилка: {data.get('error')}")

        signal = data.get("final_signal", "HOLD")
        weights = data.get("weights", {})
        details = data.get("details", {})
        smart = details.get("smart_money", {})
        
        gpt = details.get("gpt_sentiment", {})
        gpt_signal = gpt.get("signal", "HOLD")
        gpt_raw = gpt.get("raw", "No data")

        reply = f"📈 *{symbol}*\n"


        reply += "\n🧠 *Тех. аналіз:*\n"
        if "tech" in details:
            reply += f"• Стратегія: `{details['tech']}`\n"

        if "rsi" in details:
            reply += f"• RSI: `{details['rsi']}`\n"
        if "macd" in details and "macd_signal" in details:
            reply += f"• MACD: `{details['macd']}` vs сигнальна `{details['macd_signal']}`\n"
        if "volume" in details:
            reply += f"• Обʼєм: `{details['volume']}`\n"
        if "reasons" in details and details['reasons']:
            reply += f"• Причини: {', '.join(details['reasons'])}\n"

        if smart:
            reply += "\n💰 *Smart Money:*\n"
            reply += f"• Сигнал: `{smart.get('signal', '-')}` з довірою `{smart.get('confidence', '-')}`\n"
            reply += f"• Джерело: `{smart.get('source', '-')}`\n"

        if gpt_signal:
            reply += "\n🧠 *GPT-сентимент:*\n"
            reply += f"• Сигнал: `{gpt_signal}`\n"
            reply += f"• Пояснення: `{gpt_raw}`\n"
            if "error" in gpt:
                reply += f"• ⚠️ Помилка: _{gpt['error']}_\n"
        
        reply += f"\nФінальний сигнал: *{signal}*\n"
        reply += f"BUY: `{weights.get('BUY', 0):.2f}`, SELL: `{weights.get('SELL', 0):.2f}`, HOLD: `{weights.get('HOLD', 0):.2f}`\n"

        await message.answer(reply)

    except Exception as e:
        await message.answer(f"❌ Внутрішня помилка: {e}")


def start_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor.start_polling(dp, skip_updates=True)

# якщо хочеш запускати окремо:
# if __name__ == '__main__':
#     start_telegram_bot()
