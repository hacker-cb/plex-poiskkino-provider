"""Pydantic models for the subset of PoiskKino responses we consume.

Only the fields the provider actually maps are declared; everything else is
ignored. All fields are optional and defensively typed because Kinopoisk data
quality varies (e.g. ``externalId.imdb`` is frequently absent even when the
title exists).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Model(BaseModel):
    """Base for PoiskKino models: camelCase aliases, ignore unknown fields."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Rating(_Model):
    kp: float | None = None
    imdb: float | None = None
    tmdb: float | None = None
    film_critics: float | None = None
    russian_film_critics: float | None = None


class Votes(_Model):
    kp: int | None = None
    imdb: int | None = None
    tmdb: int | None = None
    film_critics: int | None = None
    russian_film_critics: int | None = None


class ExternalId(_Model):
    imdb: str | None = None
    tmdb: int | None = None


class ImageRef(_Model):
    url: str | None = None
    preview_url: str | None = None


class Name(_Model):
    name: str | None = None
    language: str | None = None
    type: str | None = None


class NamedValue(_Model):
    name: str | None = None


class Premiere(_Model):
    world: str | None = None
    russia: str | None = None
    cinema: str | None = None
    digital: str | None = None


class Movie(_Model):
    """A movie or series entry from ``/v1.4/movie*``."""

    id: int
    name: str | None = None
    alternative_name: str | None = None
    en_name: str | None = None
    type: str | None = None  # movie | tv-series | cartoon | anime | animated-series | ...
    type_number: int | None = None
    year: int | None = None
    is_series: bool | None = None
    rating: Rating | None = None
    votes: Votes | None = None
    external_id: ExternalId | None = None
    poster: ImageRef | None = None
    backdrop: ImageRef | None = None
    description: str | None = None
    short_description: str | None = None
    slogan: str | None = None
    age_rating: int | None = None
    rating_mpaa: str | None = None
    movie_length: int | None = None
    series_length: int | None = None
    genres: list[NamedValue] = []
    countries: list[NamedValue] = []
    names: list[Name] = []
    premiere: Premiere | None = None

    @property
    def kp_rating(self) -> float | None:
        """The Kinopoisk score, or ``None`` if absent/zero."""
        if self.rating is None or not self.rating.kp:
            return None
        return self.rating.kp

    @property
    def kp_votes(self) -> int | None:
        return self.votes.kp if self.votes else None

    @property
    def original_title(self) -> str | None:
        """Best original-language title (Latin name on Kinopoisk)."""
        return self.alternative_name or self.en_name

    @property
    def best_summary(self) -> str | None:
        return self.description or self.short_description

    @property
    def imdb_id(self) -> str | None:
        return self.external_id.imdb if self.external_id else None

    @property
    def tmdb_id(self) -> int | None:
        return self.external_id.tmdb if self.external_id else None


class Episode(_Model):
    id: int | None = None
    number: int | None = None
    name: str | None = None
    en_name: str | None = None
    air_date: str | None = None
    description: str | None = None
    still: ImageRef | None = None


class Season(_Model):
    id: str | None = None  # Kinopoisk returns a Mongo ObjectId string here
    movie_id: int | None = None
    number: int | None = None
    name: str | None = None
    en_name: str | None = None
    air_date: str | None = None
    episodes_count: int | None = None
    episodes: list[Episode] = []


class MovieSearchResponse(_Model):
    docs: list[Movie] = []
    total: int = 0
    limit: int = 0
    page: int = 1
    pages: int = 0


class SeasonSearchResponse(_Model):
    docs: list[Season] = []
    total: int = 0
    limit: int = 0
    page: int = 1
    pages: int = 0
