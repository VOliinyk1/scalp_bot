import openai
from app.config import OPENAI_API_KEY
from app.services.logging_service import bot_logger


openai.api_key = OPENAI_API_KEY

def analyze_sentiment(news: list[str], symbol: str, techs: dict) -> dict:
    try:
        if not news:
            news = [f"Проаналізуйте поточні настрої та прогнози на ринку для {symbol} з урахуванням технічних показників: {techs} і заганого настрою ринку"]

        prompt = "\n".join(news)

        response = openai.ChatCompletion.create(
            model="gpt-5-nano",  # або "gpt-" якщо дешевше
            messages=[
                {"role": "system", "content": "Ти фінансовий аналітик. Дай відповідь SELL, BUY або HOLD і розгорнуте пояснення. Українською мовою. Без спецсимволів. Не використовуй разом SELL, BUY і HOLD в тексті."},
                {"role": "user", "content": prompt}
            ],
        )

        content = response['choices'][0]['message']['content'].strip()

        if "BUY" in content:
            signal = "BUY"
        elif "SELL" in content:
            signal = "SELL"
        else:
            signal = "HOLD"

        # Логуємо результат GPT аналізу
        bot_logger.analysis(
            f"GPT сентимент аналіз для {symbol}",
            "GPT_SENTIMENT",
            f"{signal} - {content[:50]}..."
        )

        return {
            "signal": signal,
            "raw": content
        }

    except Exception as e:
        bot_logger.error(f"Помилка GPT сентимент аналізу для {symbol}: {e}")
        return {
            "signal": "HOLD",
            "error": str(e)
        }
