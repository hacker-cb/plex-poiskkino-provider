"""Matching a Plex item to a Kinopoisk entry."""

from .matcher import Matcher, MatchHints, parse_external_guid

__all__ = ["MatchHints", "Matcher", "parse_external_guid"]
