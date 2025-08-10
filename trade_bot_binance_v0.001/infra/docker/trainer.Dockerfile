FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir pandas numpy scikit-learn joblib
CMD ["python", "apps/trainer/run.py"]
