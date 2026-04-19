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
    ingest_http_timeout_seconds: int = 20
    ingest_gamma_page_size: int = 100
    ingest_closed_market_page_limit: int = 3
    ingest_gamma_retry_max_attempts: int = 5
    ingest_gamma_retry_base_delay_seconds: float = 0.5
    ingest_gamma_retry_max_delay_seconds: float = 8.0
    ingest_clob_batch_size: int = 25
    ingest_allow_source_payload_fallback: bool = True
    ingest_market_sync_interval_seconds: int = 900
    ingest_snapshot_interval_seconds: int = 60
    ingest_snapshot_target_size: float = 100.0
    ingest_snapshot_market_limit: int = 200
    dq_rule_version: str = "dq_v1"
    dq_run_interval_seconds: int = 120
    dq_market_limit: int = 200
    dq_snapshot_stale_after_seconds: int = 300
    dq_source_stale_after_seconds: int = 86400
    dq_max_mid_price_jump_abs: float = 0.35
    dq_warning_spread_threshold: float = 0.25
    dq_snapshot_future_tolerance_seconds: int = 15
    tagging_run_interval_seconds: int = 0
    tagging_market_limit: int = 200
    tagging_manual_review_enabled: bool = False
    trading_live_mode_enabled: bool = False
    trading_default_order_size: float = 10.0
    trading_live_bankroll_fraction: float = 0.02
    trading_live_min_notional: float = 5.0
    trading_live_max_notional: float = 25.0
    trading_live_daily_order_limit: int = 3
    trading_live_status_poll_attempts: int = 5
    trading_live_status_poll_interval_seconds: float = 2.0
    trading_live_private_key: str | None = None
    trading_live_chain_id: int = 137
    trading_live_signature_type: int = 0
    trading_live_funder_address: str | None = None
    trading_live_api_key: str | None = None
    trading_live_api_secret: str | None = None
    trading_live_api_passphrase: str | None = None
    trading_live_use_server_time: bool = True
    trading_live_retry_on_error: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
