# plex-poiskkino-provider — agent guide

A small **Plex Custom Metadata Provider** (HTTP service) that adds **Kinopoisk
(Кинопоиск)** ratings — and optionally Russian posters/descriptions — to movies
and TV shows in Plex, sourced from the **PoiskKino** API (a kinopoisk.dev clone).
Plex Media Server (1.43.0+) calls it as a metadata source.

## Project structure

```
src/poiskkino_provider/
  app.py            FastAPI app factory (create_app); wires routes + service
  __main__.py       `python -m poiskkino_provider` entrypoint (uvicorn)
  config.py         Settings (env POISKKINO_*), RatingImage / RatingType enums
  service.py        ProviderService — orchestrates match → fetch → map
  cache.py          tiny in-memory TTL cache
  logging_config.py logging setup
  poiskkino/        PoiskKino API client (hand-written, NO codegen)
    client.py         async httpx client
    models.py         pydantic v2 models for API responses (Movie/Season/Episode)
    errors.py         PoiskKinoError
  matching/
    matcher.py        multi-tier matcher: imdb id → tmdb id → title/year search
  plex/             Plex Custom Metadata Provider HTTP contract
    models.py         response models (MediaContainer/Metadata/Rating, manifest)
    mapping.py        PoiskKino entity → Plex Metadata mapping (honours flags)
    types.py          metadata type numbers, ratingKey codec, GUID construction
  routes/
    provider.py       provider endpoints (manifest, matches, metadata, images…)
    health.py         /health
tests/              pytest suite — unit-tests the framework-free core
docs/               ARCHITECTURE.md · DEPLOY.md · RELEASING.md · openapi.poiskkino.json
deploy/             docker-compose.yml · poiskkino-provider.service (systemd)
.github/workflows/  ci.yml · docker.yml (edge images) · release-please.yml
```

Architecture in one line: a **framework-free core** (`poiskkino/` + `matching/` +
`plex/mapping.py`) holds all the logic and is fully unit-tested; the FastAPI layer
(`routes/`, `app.py`) is a thin adapter. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Conventions & gotchas

- **Python 3.11+** (3.14-slim in Docker). FastAPI + httpx + pydantic v2 +
  pydantic-settings; build backend hatchling.
- **Tooling:** `ruff` (lint+format), `mypy` (strict), `pytest`. Pre-commit and
  pre-push hooks run them — **activate the venv in the same shell** before any git
  commit/push (`. .venv/bin/activate`), or the hooks can't find ruff/mypy/pytest.
- The PoiskKino client is **hand-written on purpose** — do not introduce a code
  generator. `docs/openapi.poiskkino.json` is the upstream spec (a contract test
  checks our `selectFields` against it).
- Comments and docs are **English**; Russian only appears in user-facing fallback
  strings (e.g. `f"Сезон {n}"`) and is intentional.
- **Rating visibility gotcha:** Plex clients only render a rating that rides a
  built-in badge (`imdb`/`themoviedb`/`rottentomatoes`); a custom `kinopoisk://`
  image is stored but invisible. Default is `themoviedb` (critic slot). Changing
  the badge on an already-matched item needs a *re-match*, not a plain refresh.
  Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Security

- **Never commit the PoiskKino API token.** It lives only in a gitignored `.env`
  (and on the server). `.env.example` carries a placeholder only.
- The service has **no auth** — it must bind localhost only and never be exposed
  to the internet (the Docker port is published to `127.0.0.1`).

## Common commands

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pre-commit install && pre-commit install --hook-type pre-push
ruff check . && mypy && pytest
uvicorn poiskkino_provider.app:create_app --factory --reload   # local dev server
```

## Releases

SemVer via [release-please](https://github.com/googleapis/release-please) from
Conventional Commits — merging the bot's release PR cuts a `vX.Y.Z` tag, a GitHub
Release, and the GHCR image (`latest` = newest release, `edge` = `master`). See
[docs/RELEASING.md](docs/RELEASING.md).

## References

Plex Custom Metadata Provider API (the contract this implements):

- Announcement / overview — https://forums.plex.tv/t/announcement-custom-metadata-providers/934384
- API reference (Metadata Providers) — https://developer.plex.tv/pms/#section/API-Info/Metadata-Providers
- Official example (TMDB) — https://github.com/plexinc/tmdb-example-provider
- Legacy plugin docs (background) — https://plex-plugin-docs.readthedocs.io/en/latest/overview.html

Data source & tooling:

- PoiskKino API — https://poiskkino.dev (bot: https://t.me/poiskkinodev_bot)
- kinopoisk.dev — https://kinopoisk.dev (upstream API this mirrors)
- Kometa — https://kometa.wiki (poster-overlay route for a real Kinopoisk logo)
- release-please — https://github.com/googleapis/release-please
