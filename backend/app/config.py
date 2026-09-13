from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Virtual Race Engineer API"
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: Path = Path("data/virtual_race_engineer.db")

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 90.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VRE_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
