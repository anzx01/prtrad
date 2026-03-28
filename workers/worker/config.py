import os


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw is not None and raw != "" else default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw is not None and raw != "" else default


class WorkerSettings:
    app_env = os.getenv("APP_ENV", "development")
    app_name = os.getenv("APP_NAME", "polymarket-tail-risk")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    rule_version = os.getenv("RULE_VERSION", "dev")
    celery_broker_url = os.getenv(
        "CELERY_BROKER_URL", "sqla+sqlite:///./var/celery/broker.sqlite3"
    )
    celery_result_backend = os.getenv(
        "CELERY_RESULT_BACKEND", "db+sqlite:///./var/celery/results.sqlite3"
    )
    celery_beat_schedule_db = os.getenv(
        "CELERY_BEAT_SCHEDULE_DB", "./var/celery/celerybeat-schedule"
    )
    polymarket_gamma_api_url = os.getenv(
        "POLYMARKET_GAMMA_API_URL", "https://gamma-api.polymarket.com"
    )
    polymarket_clob_api_url = os.getenv(
        "POLYMARKET_CLOB_API_URL", "https://clob.polymarket.com"
    )
    ingest_http_timeout_seconds = _get_int("INGEST_HTTP_TIMEOUT_SECONDS", 15)
    ingest_gamma_page_size = _get_int("INGEST_GAMMA_PAGE_SIZE", 100)
    ingest_clob_batch_size = _get_int("INGEST_CLOB_BATCH_SIZE", 100)
    ingest_market_sync_interval_seconds = _get_int("INGEST_MARKET_SYNC_INTERVAL_SECONDS", 900)
    ingest_snapshot_interval_seconds = _get_int("INGEST_SNAPSHOT_INTERVAL_SECONDS", 60)
    ingest_snapshot_target_size = _get_float("INGEST_SNAPSHOT_TARGET_SIZE", 100.0)
    ingest_snapshot_market_limit = _get_int("INGEST_SNAPSHOT_MARKET_LIMIT", 200)


settings = WorkerSettings()
