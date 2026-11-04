"""Typed application errors and the shared error-response contract."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class SceneStewardError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, detail: Any = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail
        if code:
            self.code = code


class NotFoundError(SceneStewardError):
    status_code = 404
    code = "not_found"


class PermissionDenied(SceneStewardError):
    status_code = 403
    code = "permission_denied"


class Unauthenticated(SceneStewardError):
    status_code = 401
    code = "unauthenticated"


class ConflictError(SceneStewardError):
    status_code = 409
    code = "conflict"


class VersionConflict(ConflictError):
    code = "version_conflict"

    def __init__(self, message: str = "Resource was modified by another writer"):
        super().__init__(message)


class ValidationFailed(SceneStewardError):
    status_code = 422
    code = "validation_failed"


class PreconditionFailed(SceneStewardError):
    status_code = 412
    code = "precondition_failed"


class UpstreamUnavailable(SceneStewardError):
    status_code = 503
    code = "upstream_unavailable"


class RateLimited(SceneStewardError):
    status_code = 429
    code = "rate_limited"


def error_body(code: str, message: str, *, detail: Any = None, correlation_id: str | None = None) -> dict:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if detail is not None:
        body["error"]["detail"] = detail
    if correlation_id:
        body["error"]["correlation_id"] = correlation_id
    return body


def register_exception_handlers(app) -> None:
    @app.exception_handler(SceneStewardError)
    async def _app_error(request: Request, exc: SceneStewardError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, detail=exc.detail, correlation_id=correlation_id),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        # Never leak internals; the full traceback is logged server-side.
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "An unexpected error occurred", correlation_id=correlation_id),
        )
