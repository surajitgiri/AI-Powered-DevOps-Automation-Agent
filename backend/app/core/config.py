from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):

    APP_NAME: str = "OpsPilot AI"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str

    JWT_SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

     # GitHub OAuth
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str

    GITHUB_CALLBACK_URL: str = (
        "http://localhost:8000/api/v1/github/callback"
    )

    GITHUB_STATE_SECRET: str

    FRONTEND_URL: str = "http://localhost:3000"

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # Ollama (local LLM)
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # AWS
    AWS_REGION: str = "ap-south-1"
    AWS_PROFILE: Optional[str] = None
    AWS_ACCOUNT_ID: Optional[str] = None
    AWS_ECR_REPOSITORY_PREFIX: str = "opspilot"
    AWS_DEFAULT_EC2_INSTANCE_ID: Optional[str] = None
    AWS_SSM_POLL_INTERVAL: int = 5

    # Docker
    DOCKER_BUILD_CONTEXT_ROOT: str = "./docker-workspaces"
    DOCKER_DEFAULT_NETWORK: str = "bridge"
    DOCKER_BUILD_ENABLED: bool = True
    DOCKER_MAX_BUILD_CONTEXT_MB: int = 500

    # Github Clone
    GITHUB_CLONE_WORKSPACE: str = "./docker-workspaces"
    GITHUB_MAX_ARCHIVE_SIZE_MB: int = 100

    # Redis
    REDIS_URL: str = "redis://default:krGTYBbBtvU2Nn4fhDlQZxp0jiKfSV1A@redis-19240.c278.us-east-1-4.ec2.cloud.redislabs.com:19240"

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(ROOT_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
