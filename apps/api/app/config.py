from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "polymarket-tail-risk"
    log_level: str = "INFO"
    log_json: bool = False
    rule_version: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./var/data/ptr_dev.sqlite3"
    polymarket_gamma_api_url: str = "https://gamma-api.polymarket.com"
    polymarket_clob_api_url: str = "https://clob.polymarket.com"
    ingest_http_timeout_seconds: int = 15
    ingest_gamma_page_size: int = 100
    ingest_clob_batch_size: int = 100
    ingest_market_sync_interval_seconds: int = 900
    ingest_snapshot_interval_seconds: int = 60
    ingest_snapshot_target_size: float = 100.0
    ingest_snapshot_market_limit: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
