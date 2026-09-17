"""Request correlation and access logging.

Every request gets an id, every log line inside that request carries it, and the
response echoes it back as ``X-Request-ID``. When the production office says a
booking "failed at about four o'clock", that id is what turns the complaint into
a single line of log.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

logger = logging.getLogger("app.access")


def current_request_id() -> str:
    return _request_id.get()


class RequestIdFilter(logging.Filter):
    """Puts ``%(request_id)s`` within reach of any formatter."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()
        return True


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Honour an id from upstream so a trace survives a proxy hop.
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:12]
        token = _request_id.set(request_id)
        started = time.perf_counter()

        # The reset belongs to the outer `finally`: the access log below must
        # still be able to read the id it is reporting on.
        try:
            try:
                response = await call_next(request)
            except Exception:
                elapsed = (time.perf_counter() - started) * 1000
                logger.exception(
                    "%s %s failed after %.1fms",
                    request.method,
                    request.url.path,
                    elapsed,
                )
                raise

            elapsed = (time.perf_counter() - started) * 1000
            response.headers[REQUEST_ID_HEADER] = request_id
            logger.info(
                "%s %s %s %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed,
            )
            return response
        finally:
            _request_id.reset(token)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Uvicorn's own access log would duplicate the middleware's, with less in it.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
