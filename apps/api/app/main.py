import logging
import uuid

from fastapi import FastAPI, Request

from app.config import get_settings
from app.logging_utils import bind_log_context, configure_logging

settings = get_settings()
configure_logging(
    service="api",
    environment=settings.app_env,
    rule_version=settings.rule_version,
)

app = FastAPI(title="Polymarket Tail Risk API", version="0.1.0")
logger = logging.getLogger("ptr.api")


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


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

