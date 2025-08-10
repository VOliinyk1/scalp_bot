from fastapi import FastAPI
from .routers.signals import router as signals_router
from packages.storage.db import init_db

def create_app():
    init_db()
    app = FastAPI(title="AI Smart Money API")
    app.include_router(signals_router)
    return app

app = create_app()
