"""Parsing real PoiskKino payloads into models + helper properties."""

from __future__ import annotations

from poiskkino_provider.poiskkino.models import Movie, MovieSearchResponse, SeasonSearchResponse

from .support import load_fixture


def test_parse_movie_by_id() -> None:
    movie = Movie.model_validate(load_fixture("movie_by_id.json"))
    assert movie.id == 666
    assert movie.name == "Форсаж"
    assert movie.alternative_name == "The Fast and the Furious"
    assert movie.type == "movie"
    assert movie.year == 2001
    assert movie.kp_rating == 7.827
    assert movie.imdb_id == "tt0232500"
    assert movie.tmdb_id == 9799
    assert movie.original_title == "The Fast and the Furious"
    assert movie.best_summary
    assert movie.poster and movie.poster.url


def test_movie_without_external_id() -> None:
    movie = Movie.model_validate(load_fixture("movie_no_externalid.json"))
    assert movie.id == 1140005
    assert movie.kp_rating is not None
    assert movie.imdb_id is None  # Kinopoisk lacks the external id here
    assert movie.tmdb_id is None


def test_parse_show() -> None:
    movie = Movie.model_validate(load_fixture("show_by_id.json"))
    assert movie.id == 404900
    assert movie.type == "tv-series"
    assert movie.is_series is True
    assert movie.kp_rating is not None


def test_parse_search_envelope() -> None:
    envelope = MovieSearchResponse.model_validate(load_fixture("search_10lives.json"))
    assert envelope.docs
    assert any(m.alternative_name == "10 Lives" for m in envelope.docs)


def test_parse_empty_envelope() -> None:
    envelope = MovieSearchResponse.model_validate(load_fixture("movie_match_empty.json"))
    assert envelope.docs == []


def test_parse_season() -> None:
    envelope = SeasonSearchResponse.model_validate(load_fixture("season_s1.json"))
    season = envelope.docs[0]
    assert season.number == 1
    assert season.episodes
    first = season.episodes[0]
    assert first.number == 1
    assert first.name
    assert first.still and first.still.url


def test_kp_rating_zero_is_none() -> None:
    movie = Movie.model_validate({"id": 1, "rating": {"kp": 0}})
    assert movie.kp_rating is None


def test_missing_rating_is_none() -> None:
    movie = Movie.model_validate({"id": 1})
    assert movie.kp_rating is None
    assert movie.kp_votes is None
    assert movie.original_title is None
