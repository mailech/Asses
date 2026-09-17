"""Application factory and process wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text as sql

from app.api.errors import register_error_handlers
from app.api.observability import RequestContextMiddleware, configure_logging
from app.api.routes import SessionDep
from app.api.routes import router as accommodations_router
from app.config import get_settings
from app.db.session import create_schema, get_engine

logger = logging.getLogger("app")

DESCRIPTION = """
Turns a plain-English lodging request from the production office into a priced,
stored booking.

Parsing and costing are entirely rule-based: the same text always produces the
same booking, and every figure traces back to the published rate card.
""".strip()

meta_router = APIRouter(tags=["service"])


@meta_router.get("/health", summary="Liveness and database check")
def health(session: SessionDep) -> dict[str, str]:
    session.execute(sql("SELECT 1"))
    return {"status": "ok", "database": "reachable"}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    if settings.auto_create_schema:
        create_schema(get_engine())
        logger.info("Schema ready on %s", _safe_url(settings.database_url))
    else:
        logger.info(
            "Using %s; the schema is owned by migrations",
            _safe_url(settings.database_url),
        )
    yield
    get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Accommodation Manager",
        description=DESCRIPTION,
        version="1.0.0",
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs",
    )

    # Innermost first: CORS must see the response the context middleware tagged.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    register_error_handlers(app)
    app.include_router(accommodations_router)
    app.include_router(meta_router)
    return app


def _safe_url(url: str) -> str:
    """Drop credentials before a connection string reaches the log."""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    return f"{scheme}://***@{rest.rpartition('@')[2]}"


app = create_app()
