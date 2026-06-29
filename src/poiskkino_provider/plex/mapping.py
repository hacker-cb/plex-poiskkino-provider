"""Map PoiskKino entities to Plex Metadata objects, honouring the feature flags."""

from __future__ import annotations

from ..config import Settings
from ..poiskkino.models import Episode, Movie, Season
from . import types as keys
from .models import Country, Genre, GuidRef, ImageAsset, Metadata, Rating

_MS_PER_MINUTE = 60_000


def _date_part(value: str | None) -> str | None:
    """Extract ``YYYY-MM-DD`` from an ISO date/datetime string."""
    if not value:
        return None
    return value[:10]


def _movie_release_date(movie: Movie) -> str | None:
    if movie.premiere and movie.premiere.world:
        return _date_part(movie.premiere.world)
    if movie.year:
        return f"{movie.year}-01-01"
    return None


def build_ratings(movie: Movie, settings: Settings) -> list[Rating] | None:
    """The Kinopoisk score as a single audience rating (or ``None`` if missing)."""
    kp = movie.kp_rating
    if kp is None:
        return None
    return [Rating(image=settings.rating_image_identifier, type="audience", value=round(kp, 3))]


def build_guids(movie: Movie) -> list[GuidRef] | None:
    """External id mappings, to help Plex align this entry with the primary match."""
    refs: list[GuidRef] = []
    if movie.imdb_id:
        refs.append(GuidRef(id=f"imdb://{movie.imdb_id}"))
    if movie.tmdb_id:
        refs.append(GuidRef(id=f"tmdb://{movie.tmdb_id}"))
    return refs or None


def _build_main_images(movie: Movie, settings: Settings) -> list[ImageAsset] | None:
    images: list[ImageAsset] = []
    alt = movie.name or movie.original_title
    if settings.write_poster and movie.poster and movie.poster.url:
        images.append(ImageAsset(type="coverPoster", url=movie.poster.url, alt=alt))
    if settings.write_art and movie.backdrop and movie.backdrop.url:
        images.append(ImageAsset(type="background", url=movie.backdrop.url, alt=alt))
    return images or None


def _build_genres(movie: Movie, settings: Settings) -> list[Genre] | None:
    if not settings.write_genres:
        return None
    genres = [Genre(tag=g.name) for g in movie.genres if g.name]
    return genres or None


def _build_countries(movie: Movie, settings: Settings) -> list[Country] | None:
    if not settings.write_genres:
        return None
    countries = [Country(tag=c.name) for c in movie.countries if c.name]
    return countries or None


def _title(movie: Movie) -> str:
    return movie.name or movie.original_title or f"Kinopoisk #{movie.id}"


def _original_title(movie: Movie) -> str | None:
    original = movie.original_title
    if original and original != movie.name:
        return original
    return None


def movie_to_metadata(movie: Movie, settings: Settings, identifier: str) -> Metadata:
    rating_key = keys.movie_key(movie.id)
    return Metadata(
        rating_key=rating_key,
        key=keys.metadata_key(rating_key),
        guid=keys.build_guid(identifier, "movie", rating_key),
        type="movie",
        title=_title(movie),
        original_title=_original_title(movie),
        year=movie.year,
        originally_available_at=_movie_release_date(movie),
        summary=movie.best_summary if settings.write_summary else None,
        tagline=movie.slogan if settings.write_summary else None,
        duration=movie.movie_length * _MS_PER_MINUTE if movie.movie_length else None,
        thumb=movie.poster.url if settings.write_poster and movie.poster else None,
        art=movie.backdrop.url if settings.write_art and movie.backdrop else None,
        images=_build_main_images(movie, settings),
        guids=build_guids(movie),
        ratings=build_ratings(movie, settings),
        genres=_build_genres(movie, settings),
        countries=_build_countries(movie, settings),
    )


def show_to_metadata(movie: Movie, settings: Settings, identifier: str) -> Metadata:
    rating_key = keys.show_key(movie.id)
    return Metadata(
        rating_key=rating_key,
        key=keys.metadata_key(rating_key),
        guid=keys.build_guid(identifier, "show", rating_key),
        type="show",
        title=_title(movie),
        original_title=_original_title(movie),
        year=movie.year,
        originally_available_at=_movie_release_date(movie),
        summary=movie.best_summary if settings.write_summary else None,
        tagline=movie.slogan if settings.write_summary else None,
        thumb=movie.poster.url if settings.write_poster and movie.poster else None,
        art=movie.backdrop.url if settings.write_art and movie.backdrop else None,
        images=_build_main_images(movie, settings),
        guids=build_guids(movie),
        ratings=build_ratings(movie, settings),
        genres=_build_genres(movie, settings),
        countries=_build_countries(movie, settings),
    )


def season_to_metadata(
    show: Movie, season: Season, settings: Settings, identifier: str
) -> Metadata:
    number = season.number or 0
    rating_key = keys.season_key(show.id, number)
    parent_key = keys.show_key(show.id)
    return Metadata(
        rating_key=rating_key,
        key=keys.metadata_key(rating_key),
        guid=keys.build_guid(identifier, "season", rating_key),
        type="season",
        title=season.name or f"Сезон {number}",
        index=number,
        originally_available_at=_date_part(season.air_date),
        parent_rating_key=parent_key,
        parent_key=keys.metadata_key(parent_key),
        parent_guid=keys.build_guid(identifier, "show", parent_key),
        parent_type="show",
        parent_title=_title(show),
        thumb=show.poster.url if settings.write_poster and show.poster else None,
    )


def episode_to_metadata(
    show: Movie,
    season_number: int,
    episode: Episode,
    settings: Settings,
    identifier: str,
) -> Metadata:
    number = episode.number or 0
    rating_key = keys.episode_key(show.id, season_number, number)
    season_rk = keys.season_key(show.id, season_number)
    show_rk = keys.show_key(show.id)
    still_url = episode.still.url if episode.still else None
    images = (
        [ImageAsset(type="snapshot", url=still_url, alt=episode.name)]
        if settings.write_poster and still_url
        else None
    )
    return Metadata(
        rating_key=rating_key,
        key=keys.metadata_key(rating_key),
        guid=keys.build_guid(identifier, "episode", rating_key),
        type="episode",
        title=episode.name or f"Эпизод {number}",
        original_title=episode.en_name,
        index=number,
        summary=episode.description if settings.write_summary else None,
        originally_available_at=_date_part(episode.air_date),
        thumb=still_url if settings.write_poster else None,
        images=images,
        parent_rating_key=season_rk,
        parent_key=keys.metadata_key(season_rk),
        parent_guid=keys.build_guid(identifier, "season", season_rk),
        parent_type="season",
        parent_title=f"Сезон {season_number}",
        parent_index=season_number,
        grandparent_rating_key=show_rk,
        grandparent_key=keys.metadata_key(show_rk),
        grandparent_guid=keys.build_guid(identifier, "show", show_rk),
        grandparent_type="show",
        grandparent_title=_title(show),
    )
