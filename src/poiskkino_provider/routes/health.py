"""Liveness endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from .. import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__}
