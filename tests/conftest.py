"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest
import pytest_asyncio

from poiskkino_provider.app import create_app
from poiskkino_provider.config import Settings
from poiskkino_provider.matching.matcher import Matcher
from poiskkino_provider.poiskkino.client import PoiskKinoClient
from poiskkino_provider.service import ProviderService

from .support import API_BASE


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, api_token="test-token", api_base=API_BASE)


@pytest.fixture
def make_service(settings: Settings) -> Callable[..., ProviderService]:
    def _make(**overrides: Any) -> ProviderService:
        cfg = settings.model_copy(update=overrides) if overrides else settings
        client = PoiskKinoClient(cfg.api_token, base_url=cfg.api_base)
        matcher = Matcher(client, threshold=cfg.match_threshold, search_limit=cfg.search_limit)
        return ProviderService(cfg, matcher)

    return _make


@pytest.fixture
def make_client() -> Callable[[], PoiskKinoClient]:
    def _make() -> PoiskKinoClient:
        return PoiskKinoClient("test-token", base_url=API_BASE)

    return _make


@pytest_asyncio.fixture
async def http_service(
    make_service: Callable[..., ProviderService],
) -> AsyncIterator[tuple[httpx.AsyncClient, ProviderService]]:
    """An ASGI test client wired to a freshly built provider service."""
    service = make_service()
    app = create_app(service=service)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, service
    await service.aclose()
