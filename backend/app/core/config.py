from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):

    APP_NAME: str = "OpsPilot AI"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str

    JWT_SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(ROOT_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
