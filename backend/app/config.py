"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Palmi application settings. Reads from .env file."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://palmi:palmi_secret@localhost:5432/palmi"
    DATABASE_URL_SYNC: str = "postgresql://palmi:palmi_secret@localhost:5432/palmi"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Enterprise WeChat
    WECOM_BOT_ID: str = ""
    WECOM_SECRET: str = ""
    WECOM_CORP_ID: str = ""
    WECOM_AGENT_ID: str = ""

    # LLM
    LLM_PRIMARY_MODEL: str = "qwen-max"
    LLM_PRIMARY_API_KEY: str = ""
    LLM_PRIMARY_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_FALLBACK_MODEL: str = "deepseek-v3"
    LLM_FALLBACK_API_KEY: str = ""
    LLM_FALLBACK_BASE_URL: str = "https://api.deepseek.com/v1"

    # PKE
    PKE_VAULT_ROOT: str = "/data/users"
    PKE_MAX_RAW_FILES: int = 365
    PKE_COMPILE_CRON: str = "0 3 * * *"

    # Phone Call
    MAX_CALL_DURATION_SEC: int = 1800

    # Application
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
