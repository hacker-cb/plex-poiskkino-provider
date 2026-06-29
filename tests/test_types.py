"""ratingKey codec + GUID construction."""

from __future__ import annotations

import pytest

from poiskkino_provider.plex import types as keys


def test_movie_key_roundtrip() -> None:
    key = keys.movie_key(666)
    assert key == "kp-movie-666"
    parsed = keys.parse_rating_key(key)
    assert parsed is not None
    assert parsed.kind == "movie"
    assert parsed.kp_id == 666


def test_show_key_roundtrip() -> None:
    parsed = keys.parse_rating_key(keys.show_key(404900))
    assert parsed == keys.ParsedKey("show", 404900)


def test_season_key_roundtrip() -> None:
    parsed = keys.parse_rating_key(keys.season_key(404900, 2))
    assert parsed == keys.ParsedKey("season", 404900, 2)


def test_episode_key_roundtrip() -> None:
    parsed = keys.parse_rating_key(keys.episode_key(404900, 2, 7))
    assert parsed == keys.ParsedKey("episode", 404900, 2, 7)


@pytest.mark.parametrize("bad", ["", "garbage", "kp-movie-", "kp-foo-1", "plex://movie/1"])
def test_parse_rejects_invalid(bad: str) -> None:
    assert keys.parse_rating_key(bad) is None


def test_build_guid_ok() -> None:
    guid = keys.build_guid("tv.plex.agents.custom.x.movie", "movie", "kp-movie-666")
    assert guid == "tv.plex.agents.custom.x.movie://movie/kp-movie-666"


def test_build_guid_rejects_bad_rating_key() -> None:
    with pytest.raises(ValueError, match="invalid ratingKey"):
        keys.build_guid("scheme", "movie", "bad/key")


def test_metadata_key() -> None:
    assert keys.metadata_key("kp-movie-1") == "/library/metadata/kp-movie-1"
