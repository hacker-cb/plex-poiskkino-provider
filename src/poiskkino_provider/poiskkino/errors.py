"""Exceptions raised by the PoiskKino client."""

from __future__ import annotations


class PoiskKinoError(Exception):
    """Base error for any PoiskKino API failure."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PoiskKinoAuthError(PoiskKinoError):
    """Raised on 401/403 — the API token is missing, invalid or out of permissions."""


class PoiskKinoRateLimitError(PoiskKinoError):
    """Raised on 429 — the daily request quota has been exhausted."""
