from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./signals.db"
    SYMBOL: str = "BTCUSDT"
    TIMEFRAME: str = "5m"

    class Config:
        env_file = ".env"

settings = Settings()
