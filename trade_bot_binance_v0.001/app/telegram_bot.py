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
    await message.answer("Привіт! Надішли <b>/ai_signal &lt;SYMBOL&gt;</b>, напр. <code>/ai_signal ETHUSDT</code>")

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


# якщо потрібно запускати окремо:
# if __name__ == "__main__":
#     start_telegram_bot()
