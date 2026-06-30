"""PoiskKino HTTP client: URL/headers, parsing, error mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from poiskkino_provider.poiskkino.client import PoiskKinoClient
from poiskkino_provider.poiskkino.errors import (
    PoiskKinoAuthError,
    PoiskKinoError,
    PoiskKinoRateLimitError,
)

from .support import API_BASE, load_fixture


@respx.mock
async def test_get_movie_sends_token_header() -> None:
    route = respx.get(f"{API_BASE}/v1.4/movie/666").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_by_id.json"))
    )
    async with PoiskKinoClient("secret-token", base_url=API_BASE) as client:
        movie = await client.get_movie(666)
    assert movie.id == 666
    assert route.calls.last.request.headers["X-API-KEY"] == "secret-token"


@respx.mock
async def test_find_by_imdb_builds_params() -> None:
    route = respx.get(f"{API_BASE}/v1.4/movie").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_match_imdb.json"))
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await client.find_by_imdb("tt0232500")
    assert movie is not None
    assert movie.id == 666
    params = route.calls.last.request.url.params
    assert params["externalId.imdb"] == "tt0232500"
    assert params["limit"] == "1"
    assert "selectFields" in params


@respx.mock
async def test_find_by_imdb_returns_none_on_empty() -> None:
    respx.get(f"{API_BASE}/v1.4/movie").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_match_empty.json"))
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        assert await client.find_by_imdb("tt0000000") is None


@respx.mock
async def test_search_movies() -> None:
    route = respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json=load_fixture("search_10lives.json"))
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        docs = await client.search_movies("10 lives", limit=5)
    assert docs
    assert route.calls.last.request.url.params["query"] == "10 lives"


@respx.mock
async def test_find_by_tmdb() -> None:
    route = respx.get(f"{API_BASE}/v1.4/movie").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_match_imdb.json"))
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await client.find_by_tmdb(9799)
    assert movie is not None and movie.id == 666
    assert route.calls.last.request.url.params["externalId.tmdb"] == "9799"


@respx.mock
async def test_get_single_season() -> None:
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        season = await client.get_season(404900, 1)
    assert season is not None and season.number == 1


@respx.mock
async def test_get_seasons_sorted() -> None:
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        seasons = await client.get_seasons(404900)
    assert seasons and seasons[0].number == 1


@respx.mock
@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, PoiskKinoAuthError),
        (403, PoiskKinoAuthError),
        (429, PoiskKinoRateLimitError),
        (500, PoiskKinoError),
    ],
)
async def test_error_mapping(status: int, error: type[PoiskKinoError]) -> None:
    respx.get(f"{API_BASE}/v1.4/movie/1").mock(return_value=httpx.Response(status, json={}))
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        with pytest.raises(error):
            await client.get_movie(1)


@respx.mock
async def test_network_error_wrapped() -> None:
    respx.get(f"{API_BASE}/v1.4/movie/1").mock(side_effect=httpx.ConnectError("boom"))
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        with pytest.raises(PoiskKinoError, match="failed"):
            await client.get_movie(1)
