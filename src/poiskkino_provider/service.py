"""Orchestration: turns Plex provider requests into PoiskKino lookups + mappings."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from . import __version__
from .cache import TTLCache
from .config import Settings
from .matching.matcher import Matcher, MatchHints, parse_external_guid
from .plex import mapping
from .plex import types as keys
from .plex.models import (
    Children,
    Feature,
    MatchRequest,
    MediaContainer,
    MediaContainerResponse,
    MediaProvider,
    MediaProviderResponse,
    Metadata,
    ProviderType,
    Scheme,
    dump,
)
from .plex.types import (
    TYPE_EPISODE,
    TYPE_MOVIE,
    TYPE_SEASON,
    TYPE_SHOW,
    ParsedKey,
)
from .poiskkino.models import Movie, Season


class MediaKind(StrEnum):
    movie = "movie"
    tv = "tv"


class ProviderService:
    """Stateful service shared by the movie and TV provider routers."""

    def __init__(
        self,
        settings: Settings,
        matcher: Matcher,
        *,
        cache: TTLCache[str, object] | None = None,
    ) -> None:
        self._settings = settings
        self._matcher = matcher
        self._client = matcher.client
        self._cache: TTLCache[str, object] = cache or TTLCache(
            ttl_seconds=settings.cache_ttl_seconds,
            max_entries=settings.cache_max_entries,
        )

    async def aclose(self) -> None:
        """Close the underlying PoiskKino HTTP client."""
        await self._client.aclose()

    # ----------------------------------------------------------------- #
    # Identity / manifest
    # ----------------------------------------------------------------- #
    def identifier(self, kind: MediaKind) -> str:
        return (
            self._settings.movie_identifier
            if kind is MediaKind.movie
            else self._settings.tv_identifier
        )

    def manifest(self, kind: MediaKind) -> dict[str, Any]:
        identifier = self.identifier(kind)
        type_numbers = (
            [TYPE_MOVIE] if kind is MediaKind.movie else [TYPE_SHOW, TYPE_SEASON, TYPE_EPISODE]
        )
        provider = MediaProvider(
            identifier=identifier,
            title=self._settings.title,
            version=__version__,
            types=[ProviderType(type=t, schemes=[Scheme(scheme=identifier)]) for t in type_numbers],
            features=[
                Feature(type="metadata", key="/library/metadata"),
                Feature(type="match", key="/library/metadata/matches"),
            ],
        )
        return dump(MediaProviderResponse(media_provider=provider))

    # ----------------------------------------------------------------- #
    # Cached PoiskKino access
    # ----------------------------------------------------------------- #
    async def _movie(self, kp_id: int) -> Movie | None:
        cache_key = f"movie:{kp_id}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Movie):
            return cached
        movie = await self._client.get_movie(kp_id)
        self._cache.set(cache_key, movie)
        return movie

    async def _seasons(self, kp_id: int) -> list[Season]:
        cache_key = f"seasons:{kp_id}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, list):
            return cached
        seasons = await self._client.get_seasons(kp_id)
        self._cache.set(cache_key, seasons)
        return seasons

    async def _season(self, kp_id: int, number: int) -> Season | None:
        for season in await self._seasons(kp_id):
            if season.number == number:
                return season
        return None

    # ----------------------------------------------------------------- #
    # Match
    # ----------------------------------------------------------------- #
    async def match(self, kind: MediaKind, request: MatchRequest) -> dict[str, Any]:
        identifier = self.identifier(kind)
        metadata = await self._match_metadata(kind, request, identifier)
        container = MediaContainer(
            identifier=identifier,
            total_size=len(metadata),
            size=len(metadata),
            metadata=metadata or None,
        )
        return dump(MediaContainerResponse(media_container=container))

    async def _match_metadata(  # noqa: PLR0911 — type dispatch
        self, kind: MediaKind, request: MatchRequest, identifier: str
    ) -> list[Metadata]:
        settings = self._settings
        imdb_id, tmdb_id = self._external_ids(request.guid)

        if request.type == TYPE_MOVIE:
            hints = MatchHints("movie", request.title, request.year, imdb_id, tmdb_id)
            manual = request.manual == 1
            movies = await self._matcher.match_candidates(hints, limit=5 if manual else 1)
            return [mapping.movie_to_metadata(m, settings, identifier) for m in movies]

        if request.type == TYPE_SHOW:
            hints = MatchHints("show", request.title, request.year, imdb_id, tmdb_id)
            manual = request.manual == 1
            shows = await self._matcher.match_candidates(hints, limit=5 if manual else 1)
            return [mapping.show_to_metadata(m, settings, identifier) for m in shows]

        if request.type == TYPE_SEASON:
            show = await self._match_show(request.parent_title, request.year, imdb_id, tmdb_id)
            if show is None or request.index is None:
                return []
            season = await self._season(show.id, request.index)
            if season is None:
                return []
            return [mapping.season_to_metadata(show, season, settings, identifier)]

        if request.type == TYPE_EPISODE:
            show = await self._match_show(request.grandparent_title, request.year, imdb_id, tmdb_id)
            if show is None:
                return []
            episode_md = await self._episode_metadata(
                show, request.parent_index, request.index, request.date, identifier
            )
            return [episode_md] if episode_md else []

        return []

    def _external_ids(self, guid: str | None) -> tuple[str | None, int | None]:
        parsed = parse_external_guid(guid)
        if parsed is None:
            return None, None
        provider, value = parsed
        if provider == "imdb":
            return value, None
        if provider == "tmdb" and value.isdigit():
            return None, int(value)
        return None, None

    async def _match_show(
        self, title: str | None, year: int | None, imdb_id: str | None, tmdb_id: int | None
    ) -> Movie | None:
        hints = MatchHints("show", title, year, imdb_id, tmdb_id)
        return await self._matcher.match(hints)

    async def _episode_metadata(
        self,
        show: Movie,
        parent_index: int | None,
        index: int | None,
        date: str | None,
        identifier: str,
    ) -> Metadata | None:
        if parent_index is not None and index is not None:
            season = await self._season(show.id, parent_index)
            if season is None:
                return None
            for episode in season.episodes:
                if episode.number == index:
                    return mapping.episode_to_metadata(
                        show,
                        parent_index,
                        episode,
                        self._settings,
                        identifier,
                        season_name=season.name,
                    )
            return None
        if date is not None:
            target = date[:10]
            for season in await self._seasons(show.id):
                for episode in season.episodes:
                    if episode.air_date and episode.air_date[:10] == target:
                        return mapping.episode_to_metadata(
                            show,
                            season.number or 0,
                            episode,
                            self._settings,
                            identifier,
                            season_name=season.name,
                        )
        return None

    # ----------------------------------------------------------------- #
    # Metadata by ratingKey
    # ----------------------------------------------------------------- #
    async def metadata(
        self, kind: MediaKind, rating_key: str, *, include_children: bool
    ) -> dict[str, Any] | None:
        identifier = self.identifier(kind)
        item = await self._metadata_item(rating_key, identifier, include_children)
        if item is None:
            return None
        container = MediaContainer(identifier=identifier, total_size=1, size=1, metadata=[item])
        return dump(MediaContainerResponse(media_container=container))

    async def _metadata_item(  # noqa: PLR0911 — type dispatch
        self, rating_key: str, identifier: str, include_children: bool
    ) -> Metadata | None:
        parsed = keys.parse_rating_key(rating_key)
        if parsed is None:
            return None
        settings = self._settings

        if parsed.kind == "movie":
            movie = await self._movie(parsed.kp_id)
            return mapping.movie_to_metadata(movie, settings, identifier) if movie else None

        if parsed.kind == "show":
            movie = await self._movie(parsed.kp_id)
            if movie is None:
                return None
            show_md = mapping.show_to_metadata(movie, settings, identifier)
            if include_children:
                seasons = await self._seasons(movie.id)
                children = [
                    mapping.season_to_metadata(movie, s, settings, identifier) for s in seasons
                ]
                show_md.children = Children(size=len(children), metadata=children)
            return show_md

        if parsed.kind == "season":
            return await self._season_item(parsed, identifier, include_children)

        if parsed.kind == "episode":
            return await self._episode_item(parsed, identifier)

        return None

    async def _season_item(
        self, parsed: ParsedKey, identifier: str, include_children: bool
    ) -> Metadata | None:
        movie = await self._movie(parsed.kp_id)
        if movie is None or parsed.season is None:
            return None
        season = await self._season(movie.id, parsed.season)
        if season is None:
            return None
        season_md = mapping.season_to_metadata(movie, season, self._settings, identifier)
        if include_children:
            episodes = [
                mapping.episode_to_metadata(
                    movie, parsed.season, ep, self._settings, identifier, season_name=season.name
                )
                for ep in season.episodes
            ]
            season_md.children = Children(size=len(episodes), metadata=episodes)
        return season_md

    async def _episode_item(self, parsed: ParsedKey, identifier: str) -> Metadata | None:
        movie = await self._movie(parsed.kp_id)
        if movie is None or parsed.season is None or parsed.episode is None:
            return None
        season = await self._season(movie.id, parsed.season)
        if season is None:
            return None
        for episode in season.episodes:
            if episode.number == parsed.episode:
                return mapping.episode_to_metadata(
                    movie,
                    parsed.season,
                    episode,
                    self._settings,
                    identifier,
                    season_name=season.name,
                )
        return None

    # ----------------------------------------------------------------- #
    # Children / grandchildren (paged)
    # ----------------------------------------------------------------- #
    async def children(
        self, kind: MediaKind, rating_key: str, *, start: int, size: int
    ) -> dict[str, Any] | None:
        identifier = self.identifier(kind)
        parsed = keys.parse_rating_key(rating_key)
        if parsed is None:
            return None
        if parsed.kind == "show":
            movie = await self._movie(parsed.kp_id)
            if movie is None:
                return None
            items = [
                mapping.season_to_metadata(movie, s, self._settings, identifier)
                for s in await self._seasons(movie.id)
            ]
            return self._paged(identifier, items, start, size)
        if parsed.kind == "season" and parsed.season is not None:
            movie = await self._movie(parsed.kp_id)
            season = await self._season(parsed.kp_id, parsed.season) if movie else None
            if movie is None or season is None:
                return None
            items = [
                mapping.episode_to_metadata(
                    movie, parsed.season, ep, self._settings, identifier, season_name=season.name
                )
                for ep in season.episodes
            ]
            return self._paged(identifier, items, start, size)
        return None

    async def grandchildren(
        self, kind: MediaKind, rating_key: str, *, start: int, size: int
    ) -> dict[str, Any] | None:
        identifier = self.identifier(kind)
        parsed = keys.parse_rating_key(rating_key)
        if parsed is None or parsed.kind != "show":
            return None
        movie = await self._movie(parsed.kp_id)
        if movie is None:
            return None
        items: list[Metadata] = []
        for season in await self._seasons(movie.id):
            for episode in season.episodes:
                items.append(
                    mapping.episode_to_metadata(
                        movie,
                        season.number or 0,
                        episode,
                        self._settings,
                        identifier,
                        season_name=season.name,
                    )
                )
        return self._paged(identifier, items, start, size)

    def _paged(
        self, identifier: str, items: list[Metadata], start: int, size: int
    ) -> dict[str, Any]:
        offset = max(start - 1, 0)
        page = items[offset : offset + size]
        container = MediaContainer(
            offset=offset,
            total_size=len(items),
            identifier=identifier,
            size=len(page),
            metadata=page or None,
        )
        return dump(MediaContainerResponse(media_container=container))

    # ----------------------------------------------------------------- #
    # Images
    # ----------------------------------------------------------------- #
    async def images(self, kind: MediaKind, rating_key: str) -> dict[str, Any] | None:
        identifier = self.identifier(kind)
        item = await self._metadata_item(rating_key, identifier, include_children=False)
        if item is None:
            return None
        container = MediaContainer(
            identifier=identifier,
            total_size=len(item.images or []),
            size=len(item.images or []),
            images=item.images,
        )
        return dump(MediaContainerResponse(media_container=container))
