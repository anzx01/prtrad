import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_utils import bind_log_context, configure_logging
from app.routes import (
    backtests,
    calibration,
    dq,
    launch_review,
    lists,
    markets,
    monitoring,
    netev,
    reason_codes,
    reports,
    review,
    risk,
    shadow,
    tag_quality,
    tagging,
)
from middleware import request_context_middleware

settings = get_settings()
configure_logging(
    service="api",
    environment=settings.app_env,
    rule_version=settings.rule_version,
)

app = FastAPI(title="Polymarket Tail Risk API", version="0.1.0")
logger = logging.getLogger("ptr.api")
LOCAL_DEV_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=LOCAL_DEV_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(request_context_middleware)

# Register routers
app.include_router(markets.router)
app.include_router(tagging.router)
app.include_router(dq.router)
app.include_router(review.router)
app.include_router(reason_codes.router)
app.include_router(lists.router)
app.include_router(monitoring.router)
app.include_router(tag_quality.router)
app.include_router(reports.router)
app.include_router(calibration.router)
app.include_router(netev.router)
app.include_router(risk.router)
app.include_router(backtests.router)
app.include_router(shadow.router)
app.include_router(launch_review.router)


@app.get("/health")
def health():
    bound_logger = bind_log_context(logger, request_id="healthcheck")
    bound_logger.info("healthcheck ok")
    return {
        "status": "ok",
        "service": "api",
        "environment": settings.app_env,
        "rule_version": settings.rule_version,
    }
