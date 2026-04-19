import logging
import re

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    trading,
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

app.middleware("http")(request_context_middleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=LOCAL_DEV_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(trading.router)


def _build_error_response_headers(request: Request, request_id: str) -> dict[str, str]:
    headers = {"x-request-id": request_id}
    origin = request.headers.get("origin")
    if origin and re.match(LOCAL_DEV_ORIGIN_REGEX, origin):
        headers["access-control-allow-origin"] = origin
        headers["access-control-allow-credentials"] = "true"
        headers["vary"] = "Origin"
    return headers


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "-")
    bound_logger = bind_log_context(logger, request_id=request_id)
    bound_logger.exception("Unhandled API exception on %s %s", request.method, request.url.path)

    return JSONResponse(
        status_code=500,
        headers=_build_error_response_headers(request, request_id),
        content={
            "detail": "内部服务异常，请稍后重试。",
            "request_id": request_id,
        },
    )


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
