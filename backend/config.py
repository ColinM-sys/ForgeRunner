from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/forgerunner.db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DEVICE: str = "cuda"
    UPLOAD_DIR: str = "./data/uploads"
    EXPORT_DIR: str = "./data/exports"
    EMBEDDING_CACHE_DIR: str = "./data/embeddings"
    MAX_UPLOAD_SIZE_MB: int = 200
    SCORING_BATCH_SIZE: int = 256

    # Phase 2
    ARGILLA_API_URL: str = "http://localhost:6900"
    ARGILLA_API_KEY: str = ""
    LABEL_STUDIO_URL: str = "http://localhost:8080"
    LABEL_STUDIO_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
