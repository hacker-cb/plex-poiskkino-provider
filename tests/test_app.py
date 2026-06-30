"""App factory (service built from settings), lifespan, logging, and route edges."""

from __future__ import annotations

import logging
from collections.abc import Callable

import httpx
import respx
from fastapi.testclient import TestClient

from poiskkino_provider.app import create_app
from poiskkino_provider.config import Settings
from poiskkino_provider.logging_config import configure_logging
from poiskkino_provider.service import ProviderService

from .support import API_BASE, load_fixture


def test_app_built_from_settings_runs_lifespan() -> None:
    app = create_app(Settings(_env_file=None, api_token="x"))
    with TestClient(app) as client:  # context manager triggers startup + shutdown
        assert client.get("/health").status_code == 200
        assert client.get("/movie").json()["MediaProvider"]["identifier"].endswith(".movie")


def test_app_warns_on_empty_token(caplog) -> None:
    with caplog.at_level(logging.WARNING):
        create_app(Settings(_env_file=None, api_token=""))
    assert any("POISKKINO_API_TOKEN is empty" in r.message for r in caplog.records)


def test_configure_logging_is_safe() -> None:
    # basicConfig is a no-op once pytest installed handlers; just exercise both
    # the valid-level path and the invalid-level fallback without raising.
    configure_logging("DEBUG")
    configure_logging("definitely-not-a-level")


@respx.mock
async def test_http_grandchildren(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/404900").mock(
        return_value=httpx.Response(200, json=load_fixture("show_by_id.json"))
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    resp = await client.get(
        "/tv/library/metadata/kp-show-404900/grandchildren",
        headers={"X-Plex-Container-Start": "1", "X-Plex-Container-Size": "5"},
    )
    assert resp.status_code == 200
    assert resp.json()["MediaContainer"]["Metadata"][0]["type"] == "episode"


async def test_http_children_404_for_movie_key(
    http_service: tuple[httpx.AsyncClient, object],
) -> None:
    client, _ = http_service
    resp = await client.get("/tv/library/metadata/kp-movie-1/children")
    assert resp.status_code == 404


async def test_http_grandchildren_404_for_season_key(
    http_service: tuple[httpx.AsyncClient, object],
) -> None:
    client, _ = http_service
    resp = await client.get("/tv/library/metadata/kp-season-1-1/grandchildren")
    assert resp.status_code == 404


def test_make_service_accepts_injected_cache(
    make_service: Callable[..., ProviderService],
) -> None:
    service = make_service()
    assert isinstance(service, ProviderService)
