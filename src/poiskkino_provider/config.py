"""Runtime configuration, read from environment variables (prefix ``POISKKINO_``)."""

from __future__ import annotations

from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class RatingImage(StrEnum):
    """Which built-in Plex rating badge the Kinopoisk score rides under.

    Plex has no Kinopoisk icon and the badge set is fixed, so the score must be
    displayed under one of these existing identifiers.
    """

    imdb = "imdb"
    themoviedb = "themoviedb"
    rottentomatoes_ripe = "rottentomatoes_ripe"
    rottentomatoes_upright = "rottentomatoes_upright"


# Maps the friendly enum to the exact identifier strings Plex understands.
RATING_IMAGE_IDENTIFIERS: dict[RatingImage, str] = {
    RatingImage.imdb: "imdb://image.rating",
    RatingImage.themoviedb: "themoviedb://image.rating",
    RatingImage.rottentomatoes_ripe: "rottentomatoes://image.rating.ripe",
    RatingImage.rottentomatoes_upright: "rottentomatoes://image.rating.upright",
}


class Settings(BaseSettings):
    """All knobs, populated from ``POISKKINO_*`` env vars (and an optional ``.env``)."""

    model_config = SettingsConfigDict(
        env_prefix="POISKKINO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- PoiskKino API ---
    api_token: str = ""
    api_base: str = "https://api.poiskkino.dev"

    # --- HTTP server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Provider identity ---
    identifier_prefix: str = "tv.plex.agents.custom.hackercb.poiskkino"
    title: str = "PoiskKino (Кинопоиск)"

    # --- What to contribute (the Kinopoisk rating is always contributed) ---
    write_poster: bool = True
    write_summary: bool = True
    write_art: bool = True
    write_genres: bool = False
    rating_image: RatingImage = RatingImage.imdb

    # --- Matching ---
    language: str = "ru"
    match_threshold: float = 0.6
    search_limit: int = 10

    # --- Caching ---
    cache_ttl_seconds: int = 86_400
    cache_max_entries: int = 4_096

    # --- HTTP client ---
    request_timeout: float = 20.0

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def rating_image_identifier(self) -> str:
        """The exact Plex rating-image string for the configured badge."""
        return RATING_IMAGE_IDENTIFIERS[self.rating_image]

    @property
    def movie_identifier(self) -> str:
        """Provider identifier (and GUID scheme) for the movie provider."""
        return f"{self.identifier_prefix}.movie"

    @property
    def tv_identifier(self) -> str:
        """Provider identifier (and GUID scheme) for the TV provider."""
        return f"{self.identifier_prefix}.tv"
