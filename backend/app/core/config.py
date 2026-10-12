from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ORCA Marine Intelligence API"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Fisheries & Satellite Data Ingestion Configuration
    incois_pfz_url: str | None = None
    incois_api_key: str | None = None
    copernicus_username: str | None = None
    copernicus_password: str | None = None
    erddap_base_url: str = "https://coastwatch.noaa.gov/erddap"
    erddap_mode: Literal["live_with_fallback", "fixture_only", "live_only"] = "live_with_fallback"
    fisheries_cache_dir: str = "data/fisheries_cache"
    fisheries_ingestion_enabled: bool = True
    fisheries_ingestion_interval_seconds: int = 3600

    # LLM Orchestrator Configuration
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    orca_llm_provider: str | None = None
    orca_llm_model: str | None = None
    orca_llm_timeout: float = 6.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()