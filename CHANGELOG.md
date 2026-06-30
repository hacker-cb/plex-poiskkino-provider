# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial Plex Custom Metadata Provider for Kinopoisk via the PoiskKino API.
- Movie provider (`/movie`) and TV provider (`/tv`): manifest, match, metadata,
  images, children/grandchildren endpoints.
- Multi-tier matching: IMDb id → TMDB id → text search with year/title/type
  disambiguation.
- Contributes Kinopoisk rating (always) plus optional Russian poster, summary,
  background art and genres, controlled by `POISKKINO_*` env vars.
- In-memory TTL cache to stay within the PoiskKino daily quota.
- Docker image + Compose deployment, systemd unit, GitHub Actions CI and
  pre-commit/pre-push hooks.
