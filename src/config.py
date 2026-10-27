from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str = "judgeai"
    POSTGRES_PASSWORD: str = "judgeai"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "judgeai"
    # Disable connection pooling (tests: every test gets its own event loop).
    DB_NULL_POOL: bool = False

    UPLOAD_DIR: str = "uploads"
    UPLOAD_MAX_MB: int = 50
    UPLOAD_ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt,.md"

    # "openai" = any OpenAI-compatible /chat/completions endpoint; "deepseek_web" = local
    # DeepSeek web proxy (dev only); "fake" = deterministic local stub for development and
    # tests (never silently used as a fallback).
    LLM_PROVIDER: Literal["openai", "deepseek_web", "fake"] = "openai"
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 120.0

    EMBEDDING_MODEL: str = "alekseevpavel04/multilingual-e5-small-ru-law"
    EMBEDDING_DIM: int = 384
    EMBEDDING_CACHE_DIR: str = ".fastembed_cache"
    EMBEDDING_CHUNK_SIZE: int = 2500
    EMBEDDING_MAX_CHUNKS: int = 8

    # Comma-separated. "*" keeps the previous behaviour; narrow it before any real deployment.
    CORS_ORIGINS: str = "*"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def allowed_extensions(self) -> set[str]:
        return {e.strip().lower() for e in self.UPLOAD_ALLOWED_EXTENSIONS.split(",") if e.strip()}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
