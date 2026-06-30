"""Runtime configuration, read from environment variables (prefix ``POISKKINO_``)."""

from __future__ import annotations

from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class RatingImage(StrEnum):
    """Which rating-badge identifier the Kinopoisk score is published under.

    Plex has no Kinopoisk icon. ``kinopoisk`` sends a custom image scheme that
    Plex stores verbatim and the web client renders as the number next to a
    generic star (honest — it doesn't pretend to be IMDb/TMDb). The other values
    ride a built-in branded badge: the official icon shows, but it mislabels the
    source. Built-in icons are a closed set, so a real Kinopoisk logo isn't
    possible via the rating field (only a poster overlay could do that).
    """

    kinopoisk = "kinopoisk"
    imdb = "imdb"
    themoviedb = "themoviedb"
    rottentomatoes_ripe = "rottentomatoes_ripe"
    rottentomatoes_upright = "rottentomatoes_upright"


# Maps the friendly enum to the exact identifier strings Plex stores.
RATING_IMAGE_IDENTIFIERS: dict[RatingImage, str] = {
    RatingImage.kinopoisk: "kinopoisk://image.rating",
    RatingImage.imdb: "imdb://image.rating",
    RatingImage.themoviedb: "themoviedb://image.rating",
    RatingImage.rottentomatoes_ripe: "rottentomatoes://image.rating.ripe",
    RatingImage.rottentomatoes_upright: "rottentomatoes://image.rating.upright",
}


class RatingType(StrEnum):
    """Plex rating slot. ``critic`` is required for the custom-image number to
    render (the web client's generic numeric fallback keys off the critic value)
    and is also the slot Plex Movie most often leaves free."""

    critic = "critic"
    audience = "audience"


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
    # Safe default: bind localhost only (the provider API has no auth). The
    # Docker image overrides this to 0.0.0.0 via ENV, and its published port is
    # bound to 127.0.0.1 on the host so the service still isn't world-reachable.
    host: str = "127.0.0.1"
    port: int = 8000

    # --- Provider identity ---
    identifier_prefix: str = "tv.plex.agents.custom.hackercb.poiskkino"
    title: str = "PoiskKino (Кинопоиск)"

    # --- What to contribute (the Kinopoisk rating is always contributed) ---
    write_poster: bool = True
    write_summary: bool = True
    write_art: bool = True
    write_genres: bool = False
    rating_image: RatingImage = RatingImage.kinopoisk
    rating_type: RatingType = RatingType.critic

    # --- Matching ---
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
