"""Multi-tier matching: external id (imdb -> tmdb) then text search with disambiguation.

Kinopoisk often lacks ``externalId`` even when it has the title, so the text
fallback is a common path, not an edge case. Text candidates are disambiguated
by title similarity, release year and media type to avoid false matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from ..poiskkino.client import PoiskKinoClient
from ..poiskkino.models import Movie

_GUID_RE = re.compile(r"^([a-zA-Z0-9.]+)://(.+)$")
_NON_ALNUM = re.compile(r"[^0-9a-zа-яё]+", re.IGNORECASE)  # noqa: RUF001 — Cyrillic range is intentional

# Kinopoisk ``type`` values acceptable for each Plex media kind.
MOVIE_KP_TYPES = frozenset({"movie", "cartoon", "anime"})
SHOW_KP_TYPES = frozenset({"tv-series", "animated-series", "anime"})


@dataclass(frozen=True)
class MatchHints:
    """Normalized hints extracted from a Plex match request."""

    media_type: str  # "movie" or "show"
    title: str | None = None
    year: int | None = None
    imdb_id: str | None = None
    tmdb_id: int | None = None


def parse_external_guid(guid: str | None) -> tuple[str, str] | None:
    """Parse an external GUID like ``imdb://tt0232500`` into ``(provider, id)``."""
    if not guid:
        return None
    match = _GUID_RE.match(guid.strip())
    if not match:
        return None
    # Plex GUIDs may carry a query/fragment suffix, e.g. ``imdb://tt0232500?lang=en``.
    value = match.group(2).split("?", 1)[0].split("#", 1)[0]
    return match.group(1).lower(), value


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return _NON_ALNUM.sub(" ", value).casefold().strip()


def _title_similarity(query: str | None, movie: Movie) -> float:
    norm_query = _normalize(query)
    if not norm_query:
        return 0.0
    candidates = (movie.name, movie.alternative_name, movie.en_name)
    best = 0.0
    for candidate in candidates:
        norm_candidate = _normalize(candidate)
        if not norm_candidate:
            continue
        ratio = SequenceMatcher(None, norm_query, norm_candidate).ratio()
        best = max(best, ratio)
    return best


def _type_compatible(media_type: str, movie_type: str | None) -> bool:
    if movie_type is None:
        return True  # be lenient when Kinopoisk omits the type
    allowed = SHOW_KP_TYPES if media_type == "show" else MOVIE_KP_TYPES
    return movie_type in allowed


class Matcher:
    """Resolves :class:`MatchHints` to a Kinopoisk :class:`Movie`."""

    def __init__(self, client: PoiskKinoClient, *, threshold: float, search_limit: int) -> None:
        self._client = client
        self._threshold = threshold
        self._search_limit = search_limit

    async def match(self, hints: MatchHints) -> Movie | None:
        """Return the single best match, or ``None`` if nothing is confident enough."""
        results = await self.match_candidates(hints, limit=1)
        return results[0] if results else None

    async def match_candidates(self, hints: MatchHints, *, limit: int) -> list[Movie]:
        """Return up to ``limit`` candidates, best first (for manual search)."""
        # Tier 1/2: external ids are authoritative — trust them, skip scoring.
        # Still require the media type to be compatible, so a stray imdb/tmdb id
        # pointing at the wrong kind (e.g. a movie for a show request) falls
        # through to the text search instead of producing a broken match.
        if hints.imdb_id:
            movie = await self._client.find_by_imdb(hints.imdb_id)
            if movie is not None and _type_compatible(hints.media_type, movie.type):
                return [movie]
        if hints.tmdb_id:
            movie = await self._client.find_by_tmdb(hints.tmdb_id)
            if movie is not None and _type_compatible(hints.media_type, movie.type):
                return [movie]

        # Tier 3: text search with disambiguation.
        if not hints.title:
            return []
        candidates = await self._client.search_movies(hints.title, limit=self._search_limit)
        return self._rank(hints, candidates)[:limit]

    def _rank(self, hints: MatchHints, candidates: list[Movie]) -> list[Movie]:
        scored: list[tuple[float, int, int, Movie]] = []
        for movie in candidates:
            if not _type_compatible(hints.media_type, movie.type):
                continue
            similarity = _title_similarity(hints.title, movie)
            if similarity < self._threshold:
                continue
            if hints.year and movie.year and abs(hints.year - movie.year) > 1:
                continue  # wrong year — almost certainly a different title
            year_delta = abs(hints.year - movie.year) if hints.year and movie.year else 1
            scored.append((similarity, -year_delta, movie.kp_votes or 0, movie))
        # Best title match first; then closest year; then popularity (vote count).
        scored.sort(key=lambda item: item[:3], reverse=True)
        return [item[3] for item in scored]
