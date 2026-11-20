"""Server-side configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    demo_auth_enabled: bool = True
    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_origins: list[str] = ["http://127.0.0.1:5173", "http://127.0.0.1:5174"]
    provider_approved: bool = False
    model_provider: str = "openrouter"
    model_name: str = "qwen/qwen3.7-flash"
    model_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
