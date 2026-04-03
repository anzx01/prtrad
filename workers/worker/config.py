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
    dq_rule_version = os.getenv("DQ_RULE_VERSION", "dq_v1")
    dq_run_interval_seconds = _get_int("DQ_RUN_INTERVAL_SECONDS", 120)
    dq_market_limit = _get_int("DQ_MARKET_LIMIT", 200)
    dq_snapshot_stale_after_seconds = _get_int("DQ_SNAPSHOT_STALE_AFTER_SECONDS", 300)
    dq_source_stale_after_seconds = _get_int("DQ_SOURCE_STALE_AFTER_SECONDS", 86400)
    dq_max_mid_price_jump_abs = _get_float("DQ_MAX_MID_PRICE_JUMP_ABS", 0.35)
    dq_warning_spread_threshold = _get_float("DQ_WARNING_SPREAD_THRESHOLD", 0.25)
    dq_snapshot_future_tolerance_seconds = _get_int("DQ_SNAPSHOT_FUTURE_TOLERANCE_SECONDS", 15)
    tagging_run_interval_seconds = _get_int("TAGGING_RUN_INTERVAL_SECONDS", 0)
    tagging_market_limit = _get_int("TAGGING_MARKET_LIMIT", 200)
    scoring_run_interval_seconds = _get_int("SCORING_RUN_INTERVAL_SECONDS", 180)
    scoring_market_limit = _get_int("SCORING_MARKET_LIMIT", 200)


settings = WorkerSettings()
