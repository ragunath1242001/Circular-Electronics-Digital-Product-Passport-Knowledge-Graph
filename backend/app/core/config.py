from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Digital Product Passport"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    public_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "dpp"
    postgres_user: str = "dpp"
    postgres_password: str = ""
    fuseki_url: str = "http://localhost:3030/dpp"
    quality_weight_completeness: float = Field(default=0.30, ge=0)
    quality_weight_conformance: float = Field(default=0.25, ge=0)
    quality_weight_provenance: float = Field(default=0.20, ge=0)
    quality_weight_vocabulary: float = Field(default=0.15, ge=0)
    quality_weight_reference_integrity: float = Field(default=0.10, ge=0)

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
