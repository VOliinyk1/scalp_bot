# Trade Bot — Smart Money Skeleton

## Run locally
```bash
pip install fastapi uvicorn SQLAlchemy "pydantic>=2" pandas numpy scikit-learn joblib
uvicorn apps.api.app.main:app --reload
python apps/worker/run.py
```

## Env
Copy `.env.example` to `.env` and adjust settings.
