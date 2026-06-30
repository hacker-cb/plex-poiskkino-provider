"""Plex metadata type numbers and GUID / ratingKey construction helpers.

A Plex-compatible GUID is ``{scheme}://{metadataType}/{ratingKey}``. We encode
the Kinopoisk id (and season/episode for TV) into a self-describing ratingKey so
the metadata endpoint can resolve an item from the key alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Metadata type numbers (docs/MediaProvider.md#metadata-types-table).
TYPE_MOVIE = 1
TYPE_SHOW = 2
TYPE_SEASON = 3
TYPE_EPISODE = 4

TYPE_NAME: dict[int, str] = {
    TYPE_MOVIE: "movie",
    TYPE_SHOW: "show",
    TYPE_SEASON: "season",
    TYPE_EPISODE: "episode",
}

# ratingKey must be ``[a-zA-Z0-9_-]`` only (docs/Metadata.md#ratingkey-component).
_RATING_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_MOVIE_KEY_RE = re.compile(r"^kp-movie-(\d+)$")
_SHOW_KEY_RE = re.compile(r"^kp-show-(\d+)$")
_SEASON_KEY_RE = re.compile(r"^kp-season-(\d+)-(\d+)$")
_EPISODE_KEY_RE = re.compile(r"^kp-episode-(\d+)-(\d+)-(\d+)$")


def movie_key(kp_id: int) -> str:
    return f"kp-movie-{kp_id}"


def show_key(kp_id: int) -> str:
    return f"kp-show-{kp_id}"


def season_key(show_kp_id: int, season_number: int) -> str:
    return f"kp-season-{show_kp_id}-{season_number}"


def episode_key(show_kp_id: int, season_number: int, episode_number: int) -> str:
    return f"kp-episode-{show_kp_id}-{season_number}-{episode_number}"


@dataclass(frozen=True)
class ParsedKey:
    """A decoded ratingKey."""

    kind: str  # movie | show | season | episode
    kp_id: int
    season: int | None = None
    episode: int | None = None


def parse_rating_key(rating_key: str) -> ParsedKey | None:
    """Decode a ratingKey produced by the helpers above, or ``None`` if invalid."""
    if (m := _MOVIE_KEY_RE.match(rating_key)) is not None:
        return ParsedKey("movie", int(m.group(1)))
    if (m := _SHOW_KEY_RE.match(rating_key)) is not None:
        return ParsedKey("show", int(m.group(1)))
    if (m := _SEASON_KEY_RE.match(rating_key)) is not None:
        return ParsedKey("season", int(m.group(1)), int(m.group(2)))
    if (m := _EPISODE_KEY_RE.match(rating_key)) is not None:
        return ParsedKey("episode", int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def is_valid_rating_key(rating_key: str) -> bool:
    return bool(_RATING_KEY_RE.match(rating_key))


def build_guid(scheme: str, type_name: str, rating_key: str) -> str:
    """Construct a Plex GUID; raises ``ValueError`` for an invalid ratingKey."""
    if not is_valid_rating_key(rating_key):
        raise ValueError(f"invalid ratingKey: {rating_key!r}")
    return f"{scheme}://{type_name}/{rating_key}"


def metadata_key(rating_key: str) -> str:
    """The relative API path for an item's metadata (joined to the provider base URL)."""
    return f"/library/metadata/{rating_key}"
