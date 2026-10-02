"""
Central exception handling. Never leaks stack traces, SQL details, or secrets
to the client (Doc 05 §15, Doc 10).

HTTPExceptions pass through unchanged. Everything else becomes a generic 500
with a sanitized detail message, and the real traceback goes to the server log.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("app.errors")


def _sanitize_validation_errors(errors: list[dict]) -> list[dict]:
    """Strip request body from validation error responses."""
    out = []
    for e in errors:
        out.append({
            "loc": e.get("loc", []),
            "msg": e.get("msg", "Invalid value"),
            "type": e.get("type", "value_error"),
        })
    return out


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": _sanitize_validation_errors(exc.errors())},
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred. Please try again."},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Something went wrong. Please try again."},
        )