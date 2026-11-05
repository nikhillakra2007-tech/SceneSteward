"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings, startup_checks
from app.core.exceptions import register_exception_handlers
from app.core.logging import correlation_id_var, request_id_var, setup_logging

logger = logging.getLogger("scenesteward.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    for check in startup_checks(settings):
        logger.info("startup check", extra={"integration": check["check"]})
        if check["status"] not in ("configured",):
            logger.warning("startup configuration issue: %s -> %s", check["check"], check["status"])
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SceneSteward API",
        version="1.0.0",
        description="Participant-centred documentary production workspace — consent is versioned, audited, and human-confirmed.",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        corr_id = request.headers.get("X-Correlation-ID") or req_id
        request_id_var.set(req_id)
        correlation_id_var.set(corr_id)
        request.state.request_id = req_id
        request.state.correlation_id = corr_id

        # Body-size cap for JSON APIs (uploads go through signed storage URLs).
        content_length = request.headers.get("content-length")
        if (content_length and int(content_length) > settings.max_request_bytes
                and not request.url.path.startswith("/api/v1/storage/local/upload/")):
            return JSONResponse(status_code=413, content={"error": {"code": "payload_too_large", "message": "Request body exceeds the configured limit"}})

        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Correlation-ID"] = corr_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        from app.services.metrics import record_request
        record_request(method=request.method, endpoint=request.url.path, status_code=response.status_code, duration_ms=duration_ms)
        logger.info("request", extra={
            "method": request.method, "endpoint": request.url.path,
            "status": response.status_code, "duration_ms": duration_ms,
        })
        return response

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        from app.core.rate_limiter import EXCLUDED_PATHS, get_client_ip, get_rate_limiter

        if request.url.path in EXCLUDED_PATHS or settings.app_env == "test":
            return await call_next(request)

        limiter = get_rate_limiter(settings.redis_url)
        client_ip = get_client_ip(request, settings.resolved_trusted_proxies)
        tier_limit = limiter.get_tier_limit(request.url.path, settings.rate_limit_per_minute)

        result = limiter.check(
            key=f"{client_ip}:{request.url.path}",
            limit_per_minute=tier_limit,
        )

        if result.is_limited:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": f"Too many requests. Please retry in {result.reset_seconds} seconds.",
                        "retry_after": result.reset_seconds,
                    }
                },
                headers={
                    "Retry-After": str(result.reset_seconds),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + result.reset_seconds)),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + result.reset_seconds))
        return response

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
