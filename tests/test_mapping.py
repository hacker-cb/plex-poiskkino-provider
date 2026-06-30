"""PoiskKino -> Plex Metadata mapping, including feature flags."""

from __future__ import annotations

from poiskkino_provider.config import RatingImage, RatingType, Settings
from poiskkino_provider.plex import mapping
from poiskkino_provider.poiskkino.models import Movie, SeasonSearchResponse

from .support import load_fixture

IDENT = "tv.plex.agents.custom.test.movie"


def _settings(**over: object) -> Settings:
    base = Settings(_env_file=None, api_token="t")
    return base.model_copy(update=over) if over else base


def _forsazh() -> Movie:
    return Movie.model_validate(load_fixture("movie_by_id.json"))


def test_movie_mapping_full() -> None:
    md = mapping.movie_to_metadata(_forsazh(), _settings(), IDENT)
    assert md.rating_key == "kp-movie-666"
    assert md.guid == f"{IDENT}://movie/kp-movie-666"
    assert md.type == "movie"
    assert md.title == "Форсаж"
    assert md.original_title == "The Fast and the Furious"
    assert md.year == 2001
    assert md.summary
    assert md.thumb and md.thumb.startswith("https://")
    # Default: custom kinopoisk image as a critic rating (honest number, no fake icon).
    assert md.ratings and md.ratings[0].image == "kinopoisk://image.rating"
    assert md.ratings[0].value == 7.827
    assert md.ratings[0].type == "critic"
    ids = {g.id for g in md.guids or []}
    assert ids == {"imdb://tt0232500", "tmdb://9799"}
    assert md.originally_available_at and len(md.originally_available_at) == 10


def test_rating_image_configurable() -> None:
    settings = _settings(rating_image=RatingImage.themoviedb)
    md = mapping.movie_to_metadata(_forsazh(), settings, IDENT)
    assert md.ratings and md.ratings[0].image == "themoviedb://image.rating"


def test_rating_type_configurable() -> None:
    # Riding a known badge as an audience rating (alternative to the kinopoisk default).
    settings = _settings(rating_image=RatingImage.imdb, rating_type=RatingType.audience)
    md = mapping.movie_to_metadata(_forsazh(), settings, IDENT)
    assert md.ratings and md.ratings[0].image == "imdb://image.rating"
    assert md.ratings[0].type == "audience"


def test_flags_disable_optional_fields() -> None:
    settings = _settings(write_poster=False, write_summary=False, write_art=False)
    md = mapping.movie_to_metadata(_forsazh(), settings, IDENT)
    assert md.summary is None
    assert md.tagline is None
    assert md.thumb is None
    assert md.art is None
    assert md.images is None
    assert md.ratings  # rating is always contributed


def test_genres_flag() -> None:
    md_off = mapping.movie_to_metadata(_forsazh(), _settings(), IDENT)
    assert md_off.genres is None
    md_on = mapping.movie_to_metadata(_forsazh(), _settings(write_genres=True), IDENT)
    assert md_on.genres and len(md_on.genres) >= 1


def test_movie_without_external_id_has_no_guids() -> None:
    movie = Movie.model_validate(load_fixture("movie_no_externalid.json"))
    md = mapping.movie_to_metadata(movie, _settings(), IDENT)
    assert md.guids is None
    assert md.ratings  # but still has a Kinopoisk rating


def test_release_date_fallback_to_year() -> None:
    movie = Movie.model_validate({"id": 5, "name": "X", "year": 1999})
    md = mapping.movie_to_metadata(movie, _settings(), IDENT)
    assert md.originally_available_at == "1999-01-01"


def test_show_and_season_and_episode_mapping() -> None:
    show = Movie.model_validate(load_fixture("show_by_id.json"))
    season = SeasonSearchResponse.model_validate(load_fixture("season_s1.json")).docs[0]
    episode = season.episodes[0]

    show_md = mapping.show_to_metadata(show, _settings(), IDENT)
    assert show_md.type == "show"
    assert show_md.rating_key == "kp-show-404900"
    assert show_md.ratings

    season_md = mapping.season_to_metadata(show, season, _settings(), IDENT)
    assert season_md.type == "season"
    assert season_md.index == 1
    assert season_md.parent_guid == f"{IDENT}://show/kp-show-404900"
    assert season_md.parent_type == "show"

    ep_md = mapping.episode_to_metadata(show, 1, episode, _settings(), IDENT)
    assert ep_md.type == "episode"
    assert ep_md.rating_key == "kp-episode-404900-1-1"
    assert ep_md.index == 1
    assert ep_md.parent_index == 1
    assert ep_md.grandparent_guid == f"{IDENT}://show/kp-show-404900"
    assert ep_md.summary  # Russian episode description
    assert ep_md.thumb  # still
