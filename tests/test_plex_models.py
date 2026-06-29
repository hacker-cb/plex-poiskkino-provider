"""Serialization aliases of the Plex contract models + match request parsing."""

from __future__ import annotations

from poiskkino_provider.plex.models import (
    Children,
    GuidRef,
    ImageAsset,
    MatchRequest,
    MediaContainer,
    MediaContainerResponse,
    Metadata,
    Rating,
    dump,
)


def _movie_metadata() -> Metadata:
    return Metadata(
        rating_key="kp-movie-1",
        key="/library/metadata/kp-movie-1",
        guid="scheme://movie/kp-movie-1",
        type="movie",
        title="Форсаж",
        original_title="The Fast and the Furious",
        year=2001,
        originally_available_at="2001-06-22",
        summary="...",
        ratings=[Rating(image="imdb://image.rating", type="audience", value=7.8)],
        guids=[GuidRef(id="imdb://tt0232500")],
        images=[ImageAsset(type="coverPoster", url="https://example/p.jpg", alt="Форсаж")],
    )


def test_metadata_serializes_pascal_and_camel_keys() -> None:
    payload = dump(
        MediaContainerResponse(
            media_container=MediaContainer(
                identifier="id", total_size=1, size=1, metadata=[_movie_metadata()]
            )
        )
    )
    container = payload["MediaContainer"]
    assert container["totalSize"] == 1
    item = container["Metadata"][0]
    assert item["ratingKey"] == "kp-movie-1"
    assert item["originallyAvailableAt"] == "2001-06-22"
    assert item["originalTitle"] == "The Fast and the Furious"
    # PascalCase containers
    assert item["Rating"][0] == {"image": "imdb://image.rating", "type": "audience", "value": 7.8}
    assert item["Guid"] == [{"id": "imdb://tt0232500"}]
    assert item["Image"][0]["type"] == "coverPoster"


def test_dump_excludes_none_fields() -> None:
    item = dump(_movie_metadata())
    assert "tagline" not in item  # was None
    assert "Children" not in item


def test_children_serializes_metadata_key() -> None:
    child = _movie_metadata()
    payload = dump(Children(size=1, metadata=[child]))
    assert payload["size"] == 1
    assert payload["Metadata"][0]["ratingKey"] == "kp-movie-1"


def test_match_request_parses_camel_case() -> None:
    req = MatchRequest.model_validate(
        {
            "type": 2,
            "parentTitle": "Breaking Bad",
            "parentIndex": 1,
            "guid": "imdb://tt0903747",
            "includeChildren": 1,
        }
    )
    assert req.type == 2
    assert req.parent_title == "Breaking Bad"
    assert req.parent_index == 1
    assert req.guid == "imdb://tt0903747"
    assert req.include_children == 1


def test_match_request_ignores_unknown_fields() -> None:
    req = MatchRequest.model_validate({"type": 1, "title": "X", "somethingNew": "ignored"})
    assert req.title == "X"
