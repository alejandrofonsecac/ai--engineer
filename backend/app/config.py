from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "Virtual Race Engineer API"
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: Path = BACKEND_ROOT / "data/virtual_race_engineer.db"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = Field(default=180, gt=0, le=600)
    ollama_temperature: float = Field(default=0.2, ge=0, le=1)
    ollama_num_ctx: int = Field(default=4096, ge=2048, le=32768)
    ollama_num_predict: int = Field(default=700, ge=64, le=2048)
    ollama_keep_alive: str = Field(default="5m", pattern=r"^(0|[0-9]+[smh])$")
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8",
        env_prefix="VRE_", extra="ignore",
    )

    @field_validator("database_path")
    @classmethod
    def resolve_database_path(cls, path: Path) -> Path:
        return path if path.is_absolute() else BACKEND_ROOT / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
