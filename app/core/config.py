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


settings = Settings()
