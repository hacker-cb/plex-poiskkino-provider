"""Pydantic models for the Plex Custom Metadata Provider HTTP contract.

Response models serialize to the exact JSON Plex expects: most scalar fields are
camelCase (handled by the alias generator) while container/array fields are
PascalCase (``Image``, ``Guid``, ``Rating``, ``Metadata`` ...) and carry an
explicit ``serialization_alias``. Dump with ``by_alias=True, exclude_none=True``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Out(BaseModel):
    """Base for outgoing models: camelCase aliases, construct by python name."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# --------------------------------------------------------------------------- #
# Metadata response models
# --------------------------------------------------------------------------- #
class Rating(_Out):
    image: str
    type: str  # "audience" | "critic"
    value: float


class GuidRef(_Out):
    id: str  # e.g. "imdb://tt0232500"


class ImageAsset(_Out):
    type: str  # background | backgroundSquare | clearLogo | coverPoster | snapshot
    url: str
    alt: str | None = None


class Genre(_Out):
    tag: str


class Country(_Out):
    tag: str


class Metadata(_Out):
    rating_key: str
    key: str
    guid: str
    type: str
    title: str
    originally_available_at: str | None = None
    year: int | None = None
    summary: str | None = None
    tagline: str | None = None
    original_title: str | None = None
    content_rating: str | None = None
    duration: int | None = None
    thumb: str | None = None
    art: str | None = None
    index: int | None = None

    # Parent / grandparent (TV)
    parent_rating_key: str | None = None
    parent_key: str | None = None
    parent_guid: str | None = None
    parent_type: str | None = None
    parent_title: str | None = None
    parent_index: int | None = None
    grandparent_rating_key: str | None = None
    grandparent_key: str | None = None
    grandparent_guid: str | None = None
    grandparent_type: str | None = None
    grandparent_title: str | None = None

    # PascalCase containers
    images: list[ImageAsset] | None = Field(default=None, serialization_alias="Image")
    guids: list[GuidRef] | None = Field(default=None, serialization_alias="Guid")
    ratings: list[Rating] | None = Field(default=None, serialization_alias="Rating")
    genres: list[Genre] | None = Field(default=None, serialization_alias="Genre")
    countries: list[Country] | None = Field(default=None, serialization_alias="Country")
    children: Children | None = Field(default=None, serialization_alias="Children")


class Children(_Out):
    size: int
    metadata: list[Metadata] = Field(serialization_alias="Metadata")


class MediaContainer(_Out):
    offset: int = 0
    total_size: int = 0
    identifier: str = ""
    size: int = 0
    metadata: list[Metadata] | None = Field(default=None, serialization_alias="Metadata")
    images: list[ImageAsset] | None = Field(default=None, serialization_alias="Image")


class MediaContainerResponse(_Out):
    media_container: MediaContainer = Field(serialization_alias="MediaContainer")


# --------------------------------------------------------------------------- #
# MediaProvider manifest models
# --------------------------------------------------------------------------- #
class Scheme(_Out):
    scheme: str


class ProviderType(_Out):
    type: int
    schemes: list[Scheme] = Field(serialization_alias="Scheme")


class Feature(_Out):
    type: str  # "metadata" | "match"
    key: str


class MediaProvider(_Out):
    identifier: str
    title: str
    version: str
    types: list[ProviderType] = Field(serialization_alias="Types")
    features: list[Feature] = Field(serialization_alias="Feature")


class MediaProviderResponse(_Out):
    media_provider: MediaProvider = Field(serialization_alias="MediaProvider")


# --------------------------------------------------------------------------- #
# Match request (incoming body)
# --------------------------------------------------------------------------- #
class MatchRequest(BaseModel):
    """Body of ``POST /library/metadata/matches`` (see docs/API Endpoints.md)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    type: int
    title: str | None = None
    parent_title: str | None = None
    grandparent_title: str | None = None
    year: int | None = None
    guid: str | None = None
    index: int | None = None
    parent_index: int | None = None
    filename: str | None = None
    date: str | None = None
    manual: int | None = None
    include_children: int | None = None
    include_adult: int | None = None
    episode_order: str | None = None


# Resolve the Metadata <-> Children forward reference.
Metadata.model_rebuild()
Children.model_rebuild()


def dump(model: BaseModel) -> dict[str, Any]:
    """Serialize an outgoing model to the exact JSON shape Plex expects."""
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)
