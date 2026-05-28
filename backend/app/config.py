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
    WECOM_TOKEN: str = ""  # Callback verification token
    WECOM_ENCODING_AES_KEY: str = ""  # 43-char Base64 encoding AES key

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

    # Weather trigger
    WEATHER_LAT: float = 31.23   # Default: Shanghai
    WEATHER_LON: float = 121.47
    WEATHER_ENABLED: bool = True

    # Proactive message frequency control
    PROACTIVE_MAX_PER_DAY: int = 2
    PROACTIVE_MIN_GAP_HOURS: int = 8
    PROACTIVE_SILENCE_START: int = 22  # 22:00 — no triggers after this hour
    PROACTIVE_SILENCE_END: int = 7     # 07:00 — no triggers before this hour

    # Ops console auth
    OPS_AUTH_USER: str = "admin"
    OPS_AUTH_PASS: str = "palmi2026"

    # Configurator auth
    CONFIGURATOR_PASSWORD: str = "palmi_config_2026"
    # IMPORTANT: Override via SECRET_KEY env var in production
    SECRET_KEY: str = "palmi_dev_secret_change_in_production"  # JWT signing key

    # iLink Bot (Personal WeChat)
    ILINK_ACCOUNT_ID: str = ""
    ILINK_BOT_TOKEN: str = ""
    ILINK_BASE_URL: str = "https://ilinkai.weixin.qq.com"
    ILINK_ENABLED: bool = False

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
