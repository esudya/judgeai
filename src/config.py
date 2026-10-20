from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str = "judgeai"
    POSTGRES_PASSWORD: str = "judgeai"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "judgeai"

    UPLOAD_DIR: str = "uploads"

    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"

    EMBEDDING_MODEL: str = "alekseevpavel04/multilingual-e5-small-ru-law"
    EMBEDDING_DIM: int = 384
    EMBEDDING_CACHE_DIR: str = ".fastembed_cache"
    EMBEDDING_CHUNK_SIZE: int = 2500
    EMBEDDING_MAX_CHUNKS: int = 8

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
