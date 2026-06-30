"""Contract test: the PoiskKino fields we depend on exist in the vendored spec.

Guards against silent upstream schema drift without hitting the live API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from poiskkino_provider.poiskkino.client import MOVIE_FIELDS

SPEC_PATH = Path(__file__).resolve().parent.parent / "docs" / "openapi.poiskkino.json"

# Top-level Movie fields the client/mapper rely on.
REQUIRED_MOVIE_FIELDS = {
    "id",
    "name",
    "alternativeName",
    "enName",
    "type",
    "year",
    "isSeries",
    "rating",
    "votes",
    "externalId",
    "poster",
    "backdrop",
    "description",
    "shortDescription",
    "ageRating",
    "ratingMpaa",
    "movieLength",
    "genres",
    "premiere",
}


def _all_property_names(node: Any, acc: set[str]) -> None:
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            acc.update(props.keys())
        for value in node.values():
            _all_property_names(value, acc)
    elif isinstance(node, list):
        for item in node:
            _all_property_names(item, acc)


@pytest.fixture(scope="module")
def property_names() -> set[str]:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    _all_property_names(spec.get("components", {}).get("schemas", spec), names)
    return names


def test_spec_present() -> None:
    assert SPEC_PATH.exists(), "vendored openapi.poiskkino.json is missing"


def test_required_movie_fields_present(property_names: set[str]) -> None:
    missing = REQUIRED_MOVIE_FIELDS - property_names
    assert not missing, f"PoiskKino spec no longer exposes: {sorted(missing)}"


def test_rating_and_external_id_subfields(property_names: set[str]) -> None:
    # Nested fields we read off rating/externalId/poster.
    for field in ("kp", "imdb", "tmdb", "url", "previewUrl"):
        assert field in property_names, f"spec missing nested field {field!r}"


@pytest.fixture(scope="module")
def movie_select_fields_enum() -> set[str]:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    params = spec["paths"]["/v1.4/movie"]["get"]["parameters"]
    select = next((p for p in params if p["name"] == "selectFields"), None)
    assert select is not None, "/v1.4/movie has no selectFields parameter in the spec"
    schema = select["schema"]
    enum = schema.get("items", schema).get("enum")
    assert enum, "spec has no selectFields enum for /v1.4/movie"
    return set(enum)


def test_client_select_fields_are_valid(movie_select_fields_enum: set[str]) -> None:
    """Every field we request via selectFields must be accepted by the API.

    The dotted form (``genres.name``) is a valid *filter* name but NOT a valid
    selectFields value — passing it makes ``/v1.4/movie`` return HTTP 400.
    """
    invalid = set(MOVIE_FIELDS) - movie_select_fields_enum
    assert not invalid, f"invalid selectFields values (API would 400): {sorted(invalid)}"
