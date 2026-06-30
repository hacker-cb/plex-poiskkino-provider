"""Multi-tier matching logic."""

from __future__ import annotations

import httpx
import respx

from poiskkino_provider.matching.matcher import Matcher, MatchHints, parse_external_guid
from poiskkino_provider.poiskkino.client import PoiskKinoClient

from .support import API_BASE, load_fixture


def _matcher(client: PoiskKinoClient, *, threshold: float = 0.6) -> Matcher:
    return Matcher(client, threshold=threshold, search_limit=10)


def test_parse_external_guid() -> None:
    assert parse_external_guid("imdb://tt0232500") == ("imdb", "tt0232500")
    assert parse_external_guid("tmdb://9799") == ("tmdb", "9799")
    assert parse_external_guid("plex://movie/abc") == ("plex", "movie/abc")
    assert parse_external_guid(None) is None
    assert parse_external_guid("garbage") is None


@respx.mock
async def test_tier1_imdb_short_circuits_search() -> None:
    imdb = respx.get(f"{API_BASE}/v1.4/movie").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_match_imdb.json"))
    )
    search = respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json={"docs": []})
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await _matcher(client).match(
            MatchHints("movie", title="Форсаж", year=2001, imdb_id="tt0232500")
        )
    assert movie is not None and movie.id == 666
    assert imdb.called
    assert not search.called  # external id is authoritative


@respx.mock
async def test_tier2_tmdb() -> None:
    tmdb = respx.get(f"{API_BASE}/v1.4/movie").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_match_imdb.json"))
    )
    search = respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json={"docs": []})
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await _matcher(client).match(MatchHints("movie", title="x", tmdb_id=9799))
    assert movie is not None and movie.id == 666
    assert tmdb.called
    assert not search.called
    assert tmdb.calls.last.request.url.params["externalId.tmdb"] == "9799"


@respx.mock
async def test_text_fallback_disambiguates() -> None:
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json=load_fixture("search_10lives.json"))
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await _matcher(client).match(MatchHints("movie", title="10 lives", year=2024))
    assert movie is not None
    assert movie.alternative_name == "10 Lives"
    assert movie.year == 2024


@respx.mock
async def test_below_threshold_returns_none() -> None:
    docs = {"docs": [{"id": 1, "name": "Совсем другое", "type": "movie", "year": 2024}]}
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(return_value=httpx.Response(200, json=docs))
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await _matcher(client).match(MatchHints("movie", title="Totally Unrelated Title"))
    assert movie is None


@respx.mock
async def test_wrong_year_filtered() -> None:
    docs = {
        "docs": [
            {
                "id": 1,
                "name": "Матрица",
                "alternativeName": "The Matrix",
                "type": "movie",
                "year": 1999,
            }
        ]
    }
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(return_value=httpx.Response(200, json=docs))
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await _matcher(client).match(MatchHints("movie", title="The Matrix", year=2050))
    assert movie is None  # 1999 vs 2050 -> rejected


@respx.mock
async def test_type_incompatible_filtered() -> None:
    docs = {
        "docs": [
            {
                "id": 1,
                "name": "Сериал",
                "alternativeName": "The Series",
                "type": "tv-series",
                "year": 2020,
            }
        ]
    }
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(return_value=httpx.Response(200, json=docs))
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        # asking for a movie, candidate is a tv-series -> filtered out
        movie = await _matcher(client).match(MatchHints("movie", title="The Series", year=2020))
    assert movie is None


@respx.mock
async def test_no_title_no_match() -> None:
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        assert await _matcher(client).match(MatchHints("movie")) is None
