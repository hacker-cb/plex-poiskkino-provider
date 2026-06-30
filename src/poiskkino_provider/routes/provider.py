"""Per-kind provider router: manifest, match, metadata, images, children."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query

from ..plex.models import MatchRequest
from ..service import MediaKind, ProviderService

_DEFAULT_PAGE_SIZE = 20


def _resolve_paging(
    start_header: int | None,
    size_header: int | None,
    start_query: int | None,
    size_query: int | None,
) -> tuple[int, int]:
    # Header takes precedence over query; use ``is not None`` so an explicit 0
    # is honoured (start is 1-based; size 0 is a valid count-only probe).
    start = start_header if start_header is not None else start_query
    size = size_header if size_header is not None else size_query
    start = 1 if start is None else max(start, 1)
    size = _DEFAULT_PAGE_SIZE if size is None else max(size, 0)
    return start, size


def make_provider_router(kind: MediaKind, service: ProviderService) -> APIRouter:
    """Build the router for one provider kind, mounted under ``/{kind}``."""
    router = APIRouter(prefix=f"/{kind.value}", tags=[kind.value])

    @router.get("")
    @router.get("/")
    async def manifest() -> dict[str, Any]:
        return service.manifest(kind)

    @router.post("/library/metadata/matches")
    async def match(request: MatchRequest) -> dict[str, Any]:
        return await service.match(kind, request)

    @router.get("/library/metadata/{rating_key}")
    async def metadata(
        rating_key: str,
        include_children: str | None = Query(None, alias="includeChildren"),
    ) -> dict[str, Any]:
        result = await service.metadata(kind, rating_key, include_children=include_children == "1")
        if result is None:
            raise HTTPException(status_code=404, detail="not found")
        return result

    @router.get("/library/metadata/{rating_key}/images")
    async def images(rating_key: str) -> dict[str, Any]:
        result = await service.images(kind, rating_key)
        if result is None:
            raise HTTPException(status_code=404, detail="not found")
        return result

    @router.get("/library/metadata/{rating_key}/children")
    async def children(
        rating_key: str,
        start_header: int | None = Header(None, alias="X-Plex-Container-Start"),
        size_header: int | None = Header(None, alias="X-Plex-Container-Size"),
        start_query: int | None = Query(None, alias="X-Plex-Container-Start"),
        size_query: int | None = Query(None, alias="X-Plex-Container-Size"),
    ) -> dict[str, Any]:
        start, size = _resolve_paging(start_header, size_header, start_query, size_query)
        result = await service.children(kind, rating_key, start=start, size=size)
        if result is None:
            raise HTTPException(status_code=404, detail="not found")
        return result

    @router.get("/library/metadata/{rating_key}/grandchildren")
    async def grandchildren(
        rating_key: str,
        start_header: int | None = Header(None, alias="X-Plex-Container-Start"),
        size_header: int | None = Header(None, alias="X-Plex-Container-Size"),
        start_query: int | None = Query(None, alias="X-Plex-Container-Start"),
        size_query: int | None = Query(None, alias="X-Plex-Container-Size"),
    ) -> dict[str, Any]:
        start, size = _resolve_paging(start_header, size_header, start_query, size_query)
        result = await service.grandchildren(kind, rating_key, start=start, size=size)
        if result is None:
            raise HTTPException(status_code=404, detail="not found")
        return result

    return router
