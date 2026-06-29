"""Service-level orchestration: TV match/metadata branches, paging, manual mode."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import respx

from poiskkino_provider.plex.models import MatchRequest
from poiskkino_provider.service import MediaKind, ProviderService

from .support import API_BASE, load_fixture


def _mock_show_and_season() -> None:
    respx.get(f"{API_BASE}/v1.4/movie/404900").mock(
        return_value=httpx.Response(200, json=load_fixture("show_by_id.json"))
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )


@respx.mock
async def test_match_season(make_service: Callable[..., ProviderService]) -> None:
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json={"docs": [load_fixture("show_by_id.json")]})
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    service = make_service()
    result = await service.match(
        MediaKind.tv, MatchRequest(type=3, parent_title="Breaking Bad", index=1, year=2008)
    )
    item = result["MediaContainer"]["Metadata"][0]
    assert item["type"] == "season"
    assert item["index"] == 1
    await service.aclose()


@respx.mock
async def test_match_episode_by_index(make_service: Callable[..., ProviderService]) -> None:
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json={"docs": [load_fixture("show_by_id.json")]})
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    service = make_service()
    result = await service.match(
        MediaKind.tv,
        MatchRequest(type=4, grandparent_title="Breaking Bad", parent_index=1, index=1),
    )
    item = result["MediaContainer"]["Metadata"][0]
    assert item["type"] == "episode"
    assert item["index"] == 1
    await service.aclose()


@respx.mock
async def test_match_episode_by_date(make_service: Callable[..., ProviderService]) -> None:
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json={"docs": [load_fixture("show_by_id.json")]})
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    service = make_service()
    result = await service.match(
        MediaKind.tv,
        MatchRequest(type=4, grandparent_title="Breaking Bad", date="2008-01-20"),
    )
    item = result["MediaContainer"]["Metadata"][0]
    assert item["type"] == "episode"
    await service.aclose()


@respx.mock
async def test_match_episode_unknown_returns_empty(
    make_service: Callable[..., ProviderService],
) -> None:
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json={"docs": [load_fixture("show_by_id.json")]})
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    service = make_service()
    result = await service.match(
        MediaKind.tv,
        MatchRequest(type=4, grandparent_title="Breaking Bad", parent_index=9, index=9),
    )
    assert result["MediaContainer"]["totalSize"] == 0
    await service.aclose()


@respx.mock
async def test_unsupported_match_type(make_service: Callable[..., ProviderService]) -> None:
    service = make_service()
    result = await service.match(MediaKind.movie, MatchRequest(type=99, title="x"))
    assert result["MediaContainer"]["totalSize"] == 0
    await service.aclose()


@respx.mock
async def test_manual_mode_returns_multiple(make_service: Callable[..., ProviderService]) -> None:
    docs = {
        "docs": [
            {"id": 1, "name": "Дубль", "alternativeName": "Double", "type": "movie", "year": 2024},
            {
                "id": 2,
                "name": "Дубль 2",
                "alternativeName": "Double",
                "type": "movie",
                "year": 2023,
            },
        ]
    }
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(return_value=httpx.Response(200, json=docs))
    service = make_service()
    result = await service.match(MediaKind.movie, MatchRequest(type=1, title="Double", manual=1))
    assert result["MediaContainer"]["size"] == 2
    await service.aclose()


@respx.mock
async def test_season_metadata_with_children(
    make_service: Callable[..., ProviderService],
) -> None:
    _mock_show_and_season()
    service = make_service()
    result = await service.metadata(MediaKind.tv, "kp-season-404900-1", include_children=True)
    assert result is not None
    item = result["MediaContainer"]["Metadata"][0]
    assert item["type"] == "season"
    assert item["Children"]["Metadata"][0]["type"] == "episode"
    await service.aclose()


@respx.mock
async def test_episode_metadata(make_service: Callable[..., ProviderService]) -> None:
    _mock_show_and_season()
    service = make_service()
    result = await service.metadata(MediaKind.tv, "kp-episode-404900-1-1", include_children=False)
    assert result is not None
    item = result["MediaContainer"]["Metadata"][0]
    assert item["type"] == "episode"
    assert item["grandparentTitle"]
    await service.aclose()


@respx.mock
async def test_grandchildren(make_service: Callable[..., ProviderService]) -> None:
    _mock_show_and_season()
    service = make_service()
    result = await service.grandchildren(MediaKind.tv, "kp-show-404900", start=1, size=20)
    assert result is not None
    assert result["MediaContainer"]["Metadata"][0]["type"] == "episode"
    await service.aclose()


@respx.mock
async def test_grandchildren_paging(make_service: Callable[..., ProviderService]) -> None:
    _mock_show_and_season()
    service = make_service()
    result = await service.grandchildren(MediaKind.tv, "kp-show-404900", start=2, size=1)
    assert result is not None
    container = result["MediaContainer"]
    assert container["offset"] == 1
    assert container["size"] == 1
    await service.aclose()


@respx.mock
async def test_episode_images(make_service: Callable[..., ProviderService]) -> None:
    _mock_show_and_season()
    service = make_service()
    result = await service.images(MediaKind.tv, "kp-episode-404900-1-1")
    assert result is not None
    images = result["MediaContainer"]["Image"]
    assert any(img["type"] == "snapshot" for img in images)
    await service.aclose()


async def test_children_of_movie_is_none(make_service: Callable[..., ProviderService]) -> None:
    service = make_service()
    assert await service.children(MediaKind.movie, "kp-movie-1", start=1, size=20) is None
    assert await service.grandchildren(MediaKind.tv, "kp-season-1-1", start=1, size=20) is None
    assert await service.metadata(MediaKind.movie, "garbage", include_children=False) is None
    await service.aclose()
