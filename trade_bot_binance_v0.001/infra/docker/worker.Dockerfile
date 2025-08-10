FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir SQLAlchemy pandas numpy
CMD ["python", "apps/worker/run.py"]
