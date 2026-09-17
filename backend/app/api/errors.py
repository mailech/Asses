"""Every failure leaves this API in the same shape.

    {"error": {"code": "...", "message": "...", "hint": "..."}}

``code`` is stable and machine-readable, ``message`` says what went wrong and
``hint`` says what to do about it -- the production office is the audience here,
not a stack trace reader.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import BookingError, BookingNotFound
from app.schemas import ErrorBody, ErrorOut

logger = logging.getLogger(__name__)

#: Spelled out rather than imported: Starlette renamed its 422 constant, and the
#: number is the part of the contract that will not move.
HTTP_422_UNPROCESSABLE = 422

BODY_HINT = 'Send {"text": "<the request in plain English>"}.'


class InvalidPayload(Exception):
    """The HTTP body itself was wrong -- before any booking rule was reached."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint or BODY_HINT


def error_response(
    status_code: int, code: str, message: str, hint: str | None = None
) -> JSONResponse:
    body = ErrorOut(error=ErrorBody(code=code, message=message, hint=hint))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidPayload)
    async def _invalid_body(_: Request, exc: InvalidPayload) -> JSONResponse:
        return error_response(
            status.HTTP_400_BAD_REQUEST, "invalid_payload", exc.message, exc.hint
        )

    @app.exception_handler(BookingNotFound)
    async def _not_found(_: Request, exc: BookingNotFound) -> JSONResponse:
        return error_response(status.HTTP_404_NOT_FOUND, exc.code, exc.message, exc.hint)

    @app.exception_handler(BookingError)
    async def _booking_error(_: Request, exc: BookingError) -> JSONResponse:
        return error_response(HTTP_422_UNPROCESSABLE, exc.code, exc.message, exc.hint)

    @app.exception_handler(RequestValidationError)
    async def _invalid_payload(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", ())[1:]) or "body"
        return error_response(
            status.HTTP_400_BAD_REQUEST,
            "invalid_payload",
            f"{field}: {first.get('msg', 'is invalid')}.",
            hint=BODY_HINT,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(
            exc.status_code, f"http_{exc.status_code}", str(exc.detail)
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "The request could not be completed.",
        )
