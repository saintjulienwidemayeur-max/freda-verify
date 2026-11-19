"""Structured error responses: {"error": {"code", "message", "request_id", "details"}}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("fv.error")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list | None = None, headers: dict | None = None):
        self.status_code, self.code, self.message, self.details, self.headers = status_code, code, message, details or [], headers


def unauthorized(message: str = "Authentication required") -> AppError:
    return AppError(401, "unauthorized", message, headers={"WWW-Authenticate": "Bearer"})


def forbidden(message: str = "You do not have permission to do this") -> AppError:
    return AppError(403, "forbidden", message)


def not_found(message: str = "Not found") -> AppError:
    return AppError(404, "not_found", message)


def _body(request: Request, code: str, message: str, details: list | None = None) -> dict:
    return {"error": {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None), "details": details or []}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app(request: Request, exc: AppError):
        return JSONResponse(_body(request, exc.code, exc.message, exc.details), exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _val(request: Request, exc: RequestValidationError):
        # never echo the submitted values (they may contain passwords): only location + message
        details = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(_body(request, "validation_error", "Invalid request", details), 422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed", 401: "unauthorized", 403: "forbidden"}.get(exc.status_code, "http_error")
        return JSONResponse(_body(request, code, str(exc.detail)), exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _any(request: Request, exc: Exception):
        log.exception("unhandled error", extra={"request_id": getattr(request.state, "request_id", None)})
        return JSONResponse(_body(request, "internal_error", "Something went wrong"), 500)
