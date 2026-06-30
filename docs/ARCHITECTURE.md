# Architecture

## Goal

Add a **Kinopoisk rating** (and optionally a Russian poster/description) to
movies and TV shows that Plex has already matched, by implementing Plex's new
**Custom Metadata Provider** HTTP API and sourcing data from the PoiskKino
(kinopoisk.dev-compatible) API.

## Layered design

A framework-free **core** holds all the logic and is fully unit-tested; the
FastAPI layer is a thin adapter. Nothing in the core imports FastAPI, so it can
be reused (e.g. by a future sidecar) and tested without an HTTP server.

```
src/poiskkino_provider/
├── config.py            # Settings (env-driven) + rating-image enum
├── cache.py             # bounded TTL cache (quota friendliness)
├── poiskkino/           # ── core: PoiskKino API ──
│   ├── client.py        #   async httpx client (get_movie, find_by_imdb/tmdb, search, seasons)
│   ├── models.py        #   pydantic models for the fields we consume
│   └── errors.py
├── matching/
│   └── matcher.py       # ── core: imdb → tmdb → text-search disambiguation ──
├── plex/                # ── core: Plex contract ──
│   ├── models.py        #   manifest + Metadata response models (exact JSON aliases)
│   ├── mapping.py       #   PoiskKino Movie/Season/Episode → Plex Metadata
│   └── types.py         #   metadata type numbers, ratingKey codec, GUID construction
├── service.py           # orchestrates core pieces; returns ready-to-serialize dicts
├── routes/              # ── adapter: FastAPI ──
│   ├── provider.py      #   per-kind router (manifest, match, metadata, images, children)
│   └── health.py
├── app.py               # FastAPI factory (mounts /movie and /tv, lifespan)
└── __main__.py          # uvicorn entry point
```

## Request flow

PMS calls one HTTP service that hosts **two providers**:

- `GET /movie` and `GET /tv` → the `MediaProvider` manifest (types + feature
  endpoints). The provider identifier doubles as the GUID scheme
  (`tv.plex.agents.custom.hackercb.poiskkino.movie` / `.tv`).
- `POST /{kind}/library/metadata/matches` → resolve a Kinopoisk entry from the
  hints and return one (or, in manual mode, several) `Metadata` objects.
- `GET /{kind}/library/metadata/{ratingKey}` → full metadata for an item; TV
  shows/seasons also serve `/children` and `/grandchildren`, and every item
  serves `/images`.

`ratingKey` is self-describing so metadata can be resolved from it alone:
`kp-movie-{id}`, `kp-show-{id}`, `kp-season-{id}-{n}`, `kp-episode-{id}-{s}-{e}`.

## Matching

`Matcher` resolves hints in tiers (external ids are authoritative; the text
fallback is common because Kinopoisk often lacks external ids):

1. `externalId.imdb` lookup;
2. `externalId.tmdb` lookup;
3. `/v1.4/movie/search` by title, then disambiguate by **title similarity**
   (`difflib`), **release year** (±1) and **media type** (movie vs series),
   accepting only matches above `POISKKINO_MATCH_THRESHOLD`.

## Mapping & the rating-icon limitation

`plex/mapping.py` converts a PoiskKino entry into a Plex `Metadata` object,
honouring the `POISKKINO_WRITE_*` flags. The Kinopoisk score is emitted as a
single `audience` rating. Plex's rating-badge identifiers are a fixed set
(`imdb`, `themoviedb`, `rottentomatoes`) — there is **no Kinopoisk icon and
custom ones are not supported** — so the score is shown under the icon chosen by
`POISKKINO_RATING_IMAGE`. This is a Plex platform limitation, documented in the
README.

## Why a Custom Metadata Provider (not a legacy `.bundle` agent)

Plex announced (Dec 2025) that it will remove the legacy Python-2 agent system
from new server releases during 2026 and replace it with this HTTP provider API.
Targeting the provider API keeps the plugin future-proof, lets it run as a
secondary source alongside *Plex Movie*, and makes it a normal,
fully-unit-testable Python 3 service.
