"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import __version__
from .config import Settings
from .matching.matcher import Matcher
from .poiskkino.client import PoiskKinoClient
from .poiskkino.errors import PoiskKinoError
from .routes.health import router as health_router
from .routes.provider import make_provider_router
from .service import MediaKind, ProviderService

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    service: ProviderService | None = None,
) -> FastAPI:
    """Create the FastAPI app.

    If ``service`` is supplied it is used as-is (tests inject one); otherwise a
    service is built from ``settings`` and its HTTP client is closed on shutdown.
    """
    settings = settings or Settings()
    owns_service = service is None
    if service is None:
        if not settings.api_token:
            logger.warning("POISKKINO_API_TOKEN is empty — PoiskKino requests will fail with 401")
        client = PoiskKinoClient(
            settings.api_token,
            base_url=settings.api_base,
            timeout=settings.request_timeout,
        )
        matcher = Matcher(
            client,
            threshold=settings.match_threshold,
            search_limit=settings.search_limit,
        )
        service = ProviderService(settings, matcher)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_service:
            await service.aclose()

    app = FastAPI(
        title="PoiskKino Plex Metadata Provider",
        version=__version__,
        lifespan=lifespan,
    )

    @app.exception_handler(PoiskKinoError)
    async def _poiskkino_error(_request: Request, exc: PoiskKinoError) -> JSONResponse:
        logger.error("PoiskKino error: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"error": "poiskkino_error", "message": str(exc)},
        )

    @app.exception_handler(ValidationError)
    async def _upstream_schema_error(_request: Request, exc: ValidationError) -> JSONResponse:
        # An upstream PoiskKino response that no longer matches our models.
        logger.error("PoiskKino response failed validation: %s", exc)
        return JSONResponse(
            status_code=502,
            content={"error": "poiskkino_schema_error", "message": "unexpected upstream response"},
        )

    app.include_router(make_provider_router(MediaKind.movie, service))
    app.include_router(make_provider_router(MediaKind.tv, service))
    app.include_router(health_router)
    return app
