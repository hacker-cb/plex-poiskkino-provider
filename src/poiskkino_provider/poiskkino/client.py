"""Async HTTP client for the PoiskKino (kinopoisk.dev-compatible) API."""

from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx

from .errors import PoiskKinoAuthError, PoiskKinoError, PoiskKinoRateLimitError
from .models import Movie, MovieSearchResponse, Season, SeasonSearchResponse

# Trimmed field set requested via ``selectFields`` to keep payloads (and the
# daily quota) small while still covering everything the mapper needs.
MOVIE_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "alternativeName",
    "enName",
    "type",
    "typeNumber",
    "year",
    "isSeries",
    "rating",
    "votes",
    "externalId",
    "poster",
    "backdrop",
    "description",
    "shortDescription",
    "slogan",
    "ageRating",
    "ratingMpaa",
    "movieLength",
    "seriesLength",
    "genres.name",
    "countries.name",
    "names",
    "premiere",
)


class PoiskKinoClient:
    """Thin async wrapper over the PoiskKino endpoints used by the provider.

    The underlying :class:`httpx.AsyncClient` may be injected (for tests); when
    constructed internally it is owned and closed by :meth:`aclose`.
    """

    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://api.poiskkino.dev",
        timeout: float = 20.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            headers={"X-API-KEY": token, "Accept": "application/json"},
            timeout=timeout,
        )

    async def __aenter__(self) -> PoiskKinoClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            response = await self._client.get(path, params=params)
        except httpx.HTTPError as exc:  # network/timeout
            raise PoiskKinoError(f"request to {path} failed: {exc}") from exc

        if response.status_code in (401, 403):
            raise PoiskKinoAuthError(
                "PoiskKino rejected the API token", status_code=response.status_code
            )
        if response.status_code == 429:
            raise PoiskKinoRateLimitError("PoiskKino daily request quota exceeded", status_code=429)
        if response.status_code >= 400:
            raise PoiskKinoError(
                f"PoiskKino returned HTTP {response.status_code} for {path}",
                status_code=response.status_code,
            )
        return response.json()

    async def get_movie(self, kp_id: int) -> Movie:
        """Fetch a single movie/series by its Kinopoisk id (full object)."""
        data = await self._get(f"/v1.4/movie/{kp_id}")
        return Movie.model_validate(data)

    async def find_by_external_id(self, source: str, value: str | int) -> Movie | None:
        """Find by an external id (``imdb`` -> tt-id, ``tmdb`` -> numeric id)."""
        data = await self._get(
            "/v1.4/movie",
            params={f"externalId.{source}": value, "limit": 1, "selectFields": list(MOVIE_FIELDS)},
        )
        envelope = MovieSearchResponse.model_validate(data)
        return envelope.docs[0] if envelope.docs else None

    async def find_by_imdb(self, imdb_id: str) -> Movie | None:
        return await self.find_by_external_id("imdb", imdb_id)

    async def find_by_tmdb(self, tmdb_id: int) -> Movie | None:
        return await self.find_by_external_id("tmdb", tmdb_id)

    async def search_movies(self, query: str, *, limit: int = 10) -> list[Movie]:
        """Relevance-ranked text search via ``/v1.4/movie/search``."""
        data = await self._get(
            "/v1.4/movie/search",
            params={"query": query, "limit": limit, "page": 1},
        )
        return MovieSearchResponse.model_validate(data).docs

    async def get_season(self, movie_id: int, number: int) -> Season | None:
        """Fetch one season (with its episodes) of a series."""
        data = await self._get(
            "/v1.4/season",
            params={"movieId": movie_id, "number": number, "limit": 1},
        )
        envelope = SeasonSearchResponse.model_validate(data)
        return envelope.docs[0] if envelope.docs else None

    async def get_seasons(self, movie_id: int, *, limit: int = 50) -> list[Season]:
        """Fetch all seasons (with episodes) of a series, sorted by number."""
        data = await self._get(
            "/v1.4/season",
            params={"movieId": movie_id, "limit": limit, "page": 1},
        )
        seasons = SeasonSearchResponse.model_validate(data).docs
        return sorted(seasons, key=lambda s: s.number or 0)
