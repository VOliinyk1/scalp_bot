import openai
from app.config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def analyze_sentiment(news: list[str], symbol: str) -> dict:
    try:
        if not news:
            news = [f"Analyze the current sentiment and market outlook for {symbol}"]

        prompt = "\n".join(news)

        response = openai.ChatCompletion.create(
            model="gpt-4o",  # або "gpt-" якщо дешевше
            messages=[
                {"role": "system", "content": "Ти фінансовий аналітик. Дай відповідь SELL, BUY або HOLD і коротке пояснення. Українською мовою."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.4,
        )

        content = response['choices'][0]['message']['content'].strip().upper()

        if "BUY" in content:
            signal = "BUY"
        elif "SELL" in content:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "signal": signal,
            "raw": content
        }

    except Exception as e:
        return {
            "signal": "HOLD",
            "error": str(e)
        }
