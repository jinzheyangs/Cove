from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，全部来自环境变量或 .env。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Cove"
    ENV: str = "dev"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://cove:cove@postgres:5432/cove"
    REDIS_URL: str = "redis://redis:6379/0"

    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000

    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    LOG_LEVEL: str = "INFO"
    AI_FAILURE_THRESHOLD: int = 5
    AI_RECOVERY_SECONDS: float = 60.0

    # 逗号分隔，例如 https://a.com,https://b.com
    CORS_ORIGINS: str = ""

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    AUTH_RATE_LIMIT_REQUESTS: int = 10
    AI_RATE_LIMIT_REQUESTS: int = 30
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCK_SECONDS: int = 900

    DAILY_GIFT_LIMIT: int = 500

    # 不设置则不校验（仅建议在内网暴露 /metrics）
    METRICS_TOKEN: str = ""

    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "cove-api"
    OTEL_EXPORTER_ENDPOINT: str = "http://localhost:4318/v1/traces"
    OTEL_SAMPLE_RATIO: float = 1.0

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
