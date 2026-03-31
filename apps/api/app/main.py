import logging

from fastapi import FastAPI

from app.config import get_settings
from app.logging_utils import bind_log_context, configure_logging
from middleware import request_context_middleware

settings = get_settings()
configure_logging(
    service="api",
    environment=settings.app_env,
    rule_version=settings.rule_version,
)

app = FastAPI(title="Polymarket Tail Risk API", version="0.1.0")
logger = logging.getLogger("ptr.api")

app.middleware("http")(request_context_middleware)


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
