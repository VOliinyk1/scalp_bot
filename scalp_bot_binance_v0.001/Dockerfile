# Вибираємо офіційний Python образ
FROM python:3.10-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо файли залежностей
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо увесь код
COPY ./app ./app
COPY .env .

# Виставляємо порт
EXPOSE 8000

# Запускаємо сервер
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
