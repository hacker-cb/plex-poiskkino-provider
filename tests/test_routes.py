"""End-to-end HTTP tests through the ASGI app with PoiskKino mocked."""

from __future__ import annotations

import httpx
import respx

from .support import API_BASE, load_fixture


async def test_health(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_movie_manifest(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    resp = await client.get("/movie")
    assert resp.status_code == 200
    provider = resp.json()["MediaProvider"]
    assert provider["identifier"].endswith(".movie")
    assert [t["type"] for t in provider["Types"]] == [1]
    feature_types = {f["type"] for f in provider["Feature"]}
    assert feature_types == {"metadata", "match"}
    assert provider["Types"][0]["Scheme"][0]["scheme"] == provider["identifier"]


async def test_tv_manifest(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    resp = await client.get("/tv")
    provider = resp.json()["MediaProvider"]
    assert provider["identifier"].endswith(".tv")
    assert sorted(t["type"] for t in provider["Types"]) == [2, 3, 4]


@respx.mock
async def test_match_movie_by_imdb(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_match_imdb.json"))
    )
    resp = await client.post(
        "/movie/library/metadata/matches",
        json={"type": 1, "title": "Форсаж", "year": 2001, "guid": "imdb://tt0232500"},
    )
    assert resp.status_code == 200
    container = resp.json()["MediaContainer"]
    assert container["identifier"].endswith(".movie")
    assert container["size"] == 1
    item = container["Metadata"][0]
    assert item["ratingKey"] == "kp-movie-666"
    assert item["guid"].endswith("://movie/kp-movie-666")
    assert item["Rating"][0]["value"] == 7.827


@respx.mock
async def test_match_movie_text_fallback(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json=load_fixture("search_10lives.json"))
    )
    resp = await client.post(
        "/movie/library/metadata/matches",
        json={"type": 1, "title": "10 lives", "year": 2024},
    )
    item = resp.json()["MediaContainer"]["Metadata"][0]
    assert item["ratingKey"] == "kp-movie-1140005"


@respx.mock
async def test_match_no_result(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_match_empty.json"))
    )
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json={"docs": []})
    )
    resp = await client.post(
        "/movie/library/metadata/matches",
        json={"type": 1, "title": "Nonexistent Zzz", "guid": "imdb://tt0000000"},
    )
    container = resp.json()["MediaContainer"]
    assert container["totalSize"] == 0
    assert "Metadata" not in container


@respx.mock
async def test_movie_metadata(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/666").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_by_id.json"))
    )
    resp = await client.get("/movie/library/metadata/kp-movie-666")
    assert resp.status_code == 200
    item = resp.json()["MediaContainer"]["Metadata"][0]
    assert item["title"] == "Форсаж"
    assert item["type"] == "movie"
    assert item["summary"]


async def test_metadata_bad_key_404(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    resp = await client.get("/movie/library/metadata/not-a-valid-key")
    assert resp.status_code == 404


@respx.mock
async def test_show_metadata_with_children(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/404900").mock(
        return_value=httpx.Response(200, json=load_fixture("show_by_id.json"))
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    resp = await client.get("/tv/library/metadata/kp-show-404900?includeChildren=1")
    item = resp.json()["MediaContainer"]["Metadata"][0]
    assert item["type"] == "show"
    assert item["Children"]["size"] >= 1
    assert item["Children"]["Metadata"][0]["type"] == "season"


@respx.mock
async def test_season_children_episodes(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/404900").mock(
        return_value=httpx.Response(200, json=load_fixture("show_by_id.json"))
    )
    respx.get(f"{API_BASE}/v1.4/season").mock(
        return_value=httpx.Response(200, json=load_fixture("season_s1.json"))
    )
    resp = await client.get("/tv/library/metadata/kp-season-404900-1/children")
    container = resp.json()["MediaContainer"]
    assert container["Metadata"][0]["type"] == "episode"
    assert container["Metadata"][0]["parentIndex"] == 1


@respx.mock
async def test_movie_images(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/666").mock(
        return_value=httpx.Response(200, json=load_fixture("movie_by_id.json"))
    )
    resp = await client.get("/movie/library/metadata/kp-movie-666/images")
    container = resp.json()["MediaContainer"]
    assert any(img["type"] == "coverPoster" for img in container["Image"])


@respx.mock
async def test_poiskkino_error_returns_502(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/666").mock(return_value=httpx.Response(500, json={}))
    resp = await client.get("/movie/library/metadata/kp-movie-666")
    assert resp.status_code == 502
    assert resp.json()["error"] == "poiskkino_error"


@respx.mock
async def test_match_show_by_text(http_service: tuple[httpx.AsyncClient, object]) -> None:
    client, _ = http_service
    respx.get(f"{API_BASE}/v1.4/movie/search").mock(
        return_value=httpx.Response(200, json={"docs": [load_fixture("show_by_id.json")]})
    )
    resp = await client.post(
        "/tv/library/metadata/matches",
        json={"type": 2, "title": "Breaking Bad", "year": 2008},
    )
    item = resp.json()["MediaContainer"]["Metadata"][0]
    assert item["ratingKey"] == "kp-show-404900"
    assert item["type"] == "show"
