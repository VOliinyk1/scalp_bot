# app/telegram_bot.py
import os
import asyncio
import requests
from html import escape as h
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # перевір, що змінна така ж у .env
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

# HTML-режим безпечніший за Markdown (менше проблем з парсингом)
bot = Bot(token=TELEGRAM_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

@dp.message_handler(commands=["start", "help"])
async def start_handler(message: types.Message):
    help_text = """
🤖 <b>Торговий бот - Команди</b>

📈 <b>AI Сигнали</b>:
<code>/ai_signal SYMBOL</code> - Повний AI аналіз
Приклад: <code>/ai_signal BTCUSDT</code>

🧠 <b>Smart Money</b>:
<code>/smart_money SYMBOL</code> - Smart Money аналіз
Приклад: <code>/smart_money ETHUSDT</code>

🗂 <b>Історія</b>:
<code>/last SYMBOL</code> - Останній збережений сигнал
Приклад: <code>/last BTCUSDT</code>

⚡ <b>Кеш</b>:
<code>/cache_stats</code> - Статистика кешу
<code>/cache_clear</code> - Очистити кеш

💡 <b>Доступні пари</b>: BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, DOTUSDT
    """
    await message.answer(help_text)

@dp.message_handler(commands=["ai_signal"])
async def ai_signal_handler(message: types.Message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            return await message.answer("❌ Використання: <code>/ai_signal &lt;SYMBOL&gt;</code>")

        symbol = parts[1].upper()
        resp = requests.get(f"{FASTAPI_URL}/signal/{symbol}", timeout=40)
        if resp.status_code != 200:
            return await message.answer("❌ Помилка сервера або неправильний символ")

        data = resp.json()

        # загальна помилка з бекенду
        if data.get("final_signal") == "ERROR":
            err = h(str(data.get("error", "Unknown error")))
            return await message.answer(f"⚠️ Помилка бекенду: <i>{err}</i>")

        # поля відповіді
        final_signal = data.get("final_signal", "HOLD")
        weights = data.get("weights", {}) or {}
        details = data.get("details", {}) or {}

        # підтримка обох ключів: gpt_sentiment / gtp_sentiment
        gpt = details.get("gpt_sentiment") or details.get("gtp_sentiment") or {}
        smart = details.get("smart_money", {}) or {}

        # опційні блоки (можуть бути відсутні, залежно від версії ai_signals)
        tf = details.get("tf", {}) or {}
        regime = details.get("regime", {}) or {}

        # заголовок
        reply = f"📈 <b>{h(symbol)}</b>\n" \
                f"Сигнал: <b>{h(str(final_signal))}</b>\n"

        # ваги
        if weights:
            reply += (
                "\n⚖️ <b>Ваги</b>: "
                f"BUY <code>{weights.get('BUY', 0):.2f}</code> · "
                f"SELL <code>{weights.get('SELL', 0):.2f}</code> · "
                f"HOLD <code>{weights.get('HOLD', 0):.2f}</code>\n"
            )

        # теханаліз: коротко (якщо є лише 'tech'), або multi-TF (якщо є 'tf')
        tech_signal = details.get("tech")
        if tech_signal:
            reply += f"\n📊 <b>Теханаліз</b>: <code>{h(str(tech_signal))}</code>\n"

        if tf:
            def tf_line(name: str) -> str:
                d = tf.get(name, {}) or {}
                sig = h(str(d.get("signal", "-")))
                rz = d.get("rsi_z")
                extras = []
                if isinstance(rz, (int, float)):
                    extras.append(f"rsi_z=<code>{rz:.2f}</code>")
                if d.get("vol_spike"):
                    extras.append("vol_spike=<code>True</code>")
                extra = (" | " + " ".join(extras)) if extras else ""
                return f"⏱ <b>{h(name)}</b>: {sig}{extra}"
            reply += (
                "\n🧭 <b>Multi-TF</b>:\n"
                + tf_line("5m") + "\n"
                + tf_line("15m") + "\n"
                + tf_line("1h") + "\n"
            )

        # режим ринку
        if regime:
            label = h(str(regime.get("label", "-")))
            adx = regime.get("adx")
            atrp = regime.get("atr_pct")
            reg_line = f"🗺 <b>Режим</b>: {label}"
            if isinstance(adx, (int, float)):
                reg_line += f" | ADX <code>{adx:.2f}</code>"
            if isinstance(atrp, (int, float)):
                reg_line += f" | ATR% <code>{atrp:.4f}</code>"
            reply += reg_line + "\n"

        # smart money
        if smart:
            sm_sig = h(str(smart.get("signal", "-")))
            sm_conf = smart.get("confidence")
            src = h(str(smart.get("source", "-")))
            reply += "💼 <b>Smart Money</b>: " \
                     f"{sm_sig} (conf=<code>{sm_conf if sm_conf is not None else '-'}</code>) · " \
                     f"src=<code>{src}</code>\n"

        # gpt sentiment
        if gpt:
            gsig = h(str(gpt.get("signal", "-")))
            gpt_msg = h(str(gpt.get("raw", "-")))
            reply += f"🧠 <b>GPT</b>: {gsig}"
            reply += f"\n{gpt_msg}"
            if gpt.get("error"):
                reply += f"\n⚠️ <i>{h(str(gpt['error']))}</i>"

        await message.answer(reply)

    except Exception as e:
        await message.answer(f"❌ Внутрішня помилка: <i>{h(str(e))}</i>")

# запуск у потоці з FastAPI
def start_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    executor.start_polling(dp, skip_updates=True)

# app/telegram_bot.py (додай)
@dp.message_handler(commands=["last"])
async def last_signal_handler(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) != 2:
        return await message.answer("❌ Використання: <code>/last &lt;SYMBOL&gt;</code>")
    symbol = parts[1].upper()
    try:
        r = requests.get(f"{FASTAPI_URL}/signals/latest/{symbol}", timeout=10)
        if r.status_code != 200:
            return await message.answer("❌ Помилка сервера")
        data = r.json()
        if not data.get("final_signal"):
            return await message.answer(f"ℹ️ Немає збережених сигналів для {symbol}")
        await message.answer(
            f"🗂 <b>Останній сигнал {symbol}</b>\n"
            f"Сигнал: <b>{data['final_signal']}</b>\n"
            f"Час: <code>{data['created_at']}</code>"
        )
    except Exception as e:
        await message.answer(f"❌ Внутрішня помилка: <i>{e}</i>")

@dp.message_handler(commands=["smart_money"])
async def smart_money_handler(message: types.Message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            return await message.answer("❌ Використання: <code>/smart_money &lt;SYMBOL&gt;</code>")

        symbol = parts[1].upper()
        resp = requests.get(f"{FASTAPI_URL}/smart_money/{symbol}", timeout=60)
        if resp.status_code != 200:
            return await message.answer("❌ Помилка сервера або неправильний символ")

        data = resp.json()

        if not data.get("success", True):
            err = h(str(data.get("error", "Unknown error")))
            return await message.answer(f"⚠️ Помилка Smart Money: <i>{err}</i>")

        # Формуємо відповідь
        reply = f"🧠 <b>Smart Money: {h(symbol)}</b>\n"
        reply += f"Сигнал: <b>{h(data['signal'])}</b>\n"
        reply += f"Впевненість: <code>{data['confidence']:.3f}</code>\n\n"
        
        reply += f"📊 <b>Ймовірності</b>:\n"
        reply += f"BUY: <code>{data['p_buy']:.3f}</code>\n"
        reply += f"SELL: <code>{data['p_sell']:.3f}</code>\n\n"
        
        reply += f"⚖️ <b>Індикатори</b>:\n"
        reply += f"Дисбаланс ордербука: <code>{data['ob_imbalance']:.4f}</code>\n"
        reply += f"Топ-трейдери: <code>{data['top_traders_ratio']:.3f}</code>\n"
        reply += f"Сентимент новин: <code>{data['news_sentiment']:.3f}</code>\n"
        reply += f"Таймфрейм: <code>{data['timeframe']}</code>"

        await message.answer(reply)

    except Exception as e:
        await message.answer(f"❌ Внутрішня помилка: <i>{h(str(e))}</i>")


@dp.message_handler(commands=["cache_stats"])
async def cache_stats_handler(message: types.Message):
    try:
        resp = requests.get(f"{FASTAPI_URL}/cache/stats", timeout=10)
        if resp.status_code != 200:
            return await message.answer("❌ Помилка сервера")
        
        data = resp.json()
        if not data.get("success"):
            return await message.answer(f"❌ Помилка: {data.get('error', 'Unknown error')}")
        
        stats = data["stats"]
        reply = f"⚡ <b>Статистика кешу</b>\n\n"
        reply += f"📊 <b>Запити</b>:\n"
        reply += f"Всього: <code>{stats['total_requests']}</code>\n"
        reply += f"Попадання: <code>{stats['hits']}</code>\n"
        reply += f"Промахи: <code>{stats['misses']}</code>\n"
        reply += f"Ефективність: <code>{stats['hit_rate']:.1%}</code>\n\n"
        reply += f"💾 <b>Розмір</b>: <code>{stats['size']}</code> записів\n"
        reply += f"🗑️ <b>Видалено</b>: <code>{stats['evictions']}</code> записів"
        
        await message.answer(reply)
        
    except Exception as e:
        await message.answer(f"❌ Внутрішня помилка: <i>{h(str(e))}</i>")

@dp.message_handler(commands=["cache_clear"])
async def cache_clear_handler(message: types.Message):
    try:
        resp = requests.post(f"{FASTAPI_URL}/cache/clear", timeout=10)
        if resp.status_code != 200:
            return await message.answer("❌ Помилка сервера")
        
        data = resp.json()
        if not data.get("success"):
            return await message.answer(f"❌ Помилка: {data.get('error', 'Unknown error')}")
        
        await message.answer("✅ Кеш успішно очищено!")
        
    except Exception as e:
        await message.answer(f"❌ Внутрішня помилка: <i>{h(str(e))}</i>")

# якщо потрібно запускати окремо:
# if __name__ == "__main__":
#     start_telegram_bot()
