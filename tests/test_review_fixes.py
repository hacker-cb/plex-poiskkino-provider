"""Regression tests for issues found and fixed during the shipping code review."""

from __future__ import annotations

import httpx
import pytest
import respx

from poiskkino_provider.config import Settings
from poiskkino_provider.matching.matcher import Matcher, MatchHints, parse_external_guid
from poiskkino_provider.plex import mapping
from poiskkino_provider.poiskkino.client import PoiskKinoClient
from poiskkino_provider.poiskkino.errors import PoiskKinoError
from poiskkino_provider.poiskkino.models import Movie, SeasonSearchResponse

from .support import API_BASE, load_fixture

IDENT = "tv.plex.agents.custom.test.tv"


def _matcher(client: PoiskKinoClient) -> Matcher:
    return Matcher(client, threshold=0.6, search_limit=10)


def test_parse_external_guid_strips_query_suffix() -> None:
    # Plex GUIDs can carry ?lang=… suffixes.
    assert parse_external_guid("tmdb://9799?lang=en-US") == ("tmdb", "9799")
    assert parse_external_guid("imdb://tt0232500?lang=en") == ("imdb", "tt0232500")


@respx.mock
async def test_external_id_type_mismatch_falls_through() -> None:
    # imdb resolves to a movie, but the request is for a show -> must fall through.
    respx.get(f"{API_BASE}/v1.4/movie").mock(
        return_value=httpx.Response(
            200, json={"docs": [{"id": 1, "type": "movie", "name": "Фильм"}]}
        )
    )
    search = respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "docs": [
                    {
                        "id": 2,
                        "type": "tv-series",
                        "name": "Шоу",
                        "alternativeName": "The Show",
                        "year": 2020,
                    }
                ]
            },
        )
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await _matcher(client).match(
            MatchHints("show", title="The Show", year=2020, imdb_id="tt1")
        )
    assert movie is not None and movie.id == 2
    assert search.called


@respx.mock
async def test_year_distance_tiebreak() -> None:
    docs = {
        "docs": [
            {"id": 1, "name": "Ремейк", "alternativeName": "Remake", "type": "movie", "year": 2011},
            {"id": 2, "name": "Ремейк", "alternativeName": "Remake", "type": "movie", "year": 2010},
        ]
    }
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(return_value=httpx.Response(200, json=docs))
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        movie = await _matcher(client).match(MatchHints("movie", title="Remake", year=2010))
    assert movie is not None and movie.id == 2  # exact-year wins over the ±1 candidate


@respx.mock
async def test_non_json_body_wrapped() -> None:
    respx.get(f"{API_BASE}/v1.4/movie/1").mock(
        return_value=httpx.Response(200, text="<html>maintenance</html>")
    )
    async with PoiskKinoClient("t", base_url=API_BASE) as client:
        with pytest.raises(PoiskKinoError):
            await client.get_movie(1)


def test_episode_uses_real_season_name() -> None:
    show = Movie.model_validate(load_fixture("show_by_id.json"))
    season = SeasonSearchResponse.model_validate(load_fixture("season_s1.json")).docs[0]
    episode = season.episodes[0]
    settings = Settings(_env_file=None, api_token="t")
    named = mapping.episode_to_metadata(show, 1, episode, settings, IDENT, season_name="Книга Огня")
    assert named.parent_title == "Книга Огня"
    fallback = mapping.episode_to_metadata(show, 1, episode, settings, IDENT)
    assert fallback.parent_title == "Сезон 1"


@respx.mock
async def test_grandchildren_size_zero_is_count_only(http_service) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/404900").mock(
        return_value=httpx.Response(200, json=load_fixture("show_by_id.json"))
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    resp = await client.get(
        "/tv/library/metadata/kp-show-404900/grandchildren",
        headers={"X-Plex-Container-Size": "0"},
    )
    container = resp.json()["MediaContainer"]
    assert container["totalSize"] >= 1
    assert container["size"] == 0  # count-only probe returns no items
    assert "Metadata" not in container


@respx.mock
async def test_invalid_upstream_schema_returns_502(http_service) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/666").mock(
        return_value=httpx.Response(200, json={"id": "not-an-int"})
    )
    resp = await client.get("/movie/library/metadata/kp-movie-666")
    assert resp.status_code == 502
    assert resp.json()["error"] == "poiskkino_schema_error"
