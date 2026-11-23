"""
SupportPilot AI — Application Configuration
Uses Pydantic BaseSettings for type-safe, env-driven config.
All secrets and sensitive settings are read from environment variables.
"""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings.
    All fields are read from environment variables (or .env file).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────
    app_name: str = "SupportPilot AI"
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # ── Security ───────────────────────────────────────────
    secret_key: str = "supportpilot_default_secret_key_32_characters_minimum"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ── Database ───────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://supportpilot:supportpilot@localhost:5432/supportpilot"
    database_url_sync: str = "postgresql://supportpilot:supportpilot@localhost:5432/supportpilot"

    # ── Redis ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── ChromaDB ───────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection_name: str = "supportpilot_docs"
    chroma_persist_dir: str = "./chroma_data"

    # ── AI Provider (configured for future phases) ──────────
    default_ai_provider: str = "gemini"
    default_model: str = "gemini-2.0-flash"
    default_embedding_model: str = "models/text-embedding-004"
    gemini_api_key: str = ""

    # ── n8n ────────────────────────────────────────────────
    n8n_webhook_url: str = ""
    n8n_api_key: str = ""

    # ── CORS ───────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    # ── Backend ────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_workers: int = 4

    # ── File Uploads ───────────────────────────────────────
    max_upload_size_mb: int = 50
    allowed_upload_types: str = "pdf,txt,md,docx,html"
    upload_dir: str = "./uploads"

    # ── Rate Limiting ──────────────────────────────────────
    rate_limit_per_minute: int = 60
    rate_limit_auth_per_minute: int = 10

    # ── Derived properties ─────────────────────────────────
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_upload_types_list(self) -> list[str]:
        return [t.strip().lower() for t in self.allowed_upload_types.split(",") if t.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
