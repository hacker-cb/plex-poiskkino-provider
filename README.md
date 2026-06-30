# plex-poiskkino-provider

A [Plex **Custom Metadata Provider**](https://forums.plex.tv/t/announcement-custom-metadata-providers/934384)
that adds **Kinopoisk (Кинопоиск)** ratings — and optionally Russian posters and
descriptions — to your movies and TV shows, sourced from the
[PoiskKino API](https://poiskkino.dev) (a kinopoisk.dev-compatible service).

It runs as a small HTTP service. Plex Media Server (**1.43.0+**) calls it as a
metadata source; you can combine it with the built-in *Plex Movie* / *Plex TV
Series* agents so Plex keeps doing the matching and our provider just contributes
the Kinopoisk data.

> **Status:** the Plex Custom Metadata Provider API is in beta (shipped Dec 2025).
> Plex plans to remove the legacy Python‑2 agent system during 2026, which is why
> this project targets the new provider API instead of a legacy `.bundle` agent.

## What it contributes

- ⭐ **Kinopoisk rating** (always) — shown as the number next to a generic star.
- 🖼️ **Russian poster** (optional) — the Kinopoisk cover.
- 📝 **Russian description** (optional) — the Kinopoisk synopsis + tagline.
- 🎬 Background art, and (optionally) genres.
- 📺 TV: show‑level rating/poster/summary plus Russian season/episode titles,
  descriptions and stills (Kinopoisk has no per‑episode ratings).

### ⚠️ Honest limitation: there is no "Kinopoisk" rating *icon*

Plex's branded rating icons are a closed set (`imdb`, `themoviedb`,
`rottentomatoes`, `thetvdb`) — a true Kinopoisk **logo** can't be added via the
rating field (only a Kometa‑style poster overlay could, which is out of scope).

The **number does show**, though. By default (`POISKKINO_RATING_IMAGE=kinopoisk`)
the provider sends a custom `kinopoisk://image.rating` as a **critic** rating;
Plex stores it verbatim and the web client renders the score next to a generic
star — honest, and it doesn't masquerade as IMDb/TMDb. (Verified on the web
client; some mobile/TV apps may render number‑only — if a client shows nothing,
switch `POISKKINO_RATING_IMAGE` to `imdb`/`themoviedb` to ride a guaranteed icon
at the cost of a mislabeled source.)

## Matching

For every item Plex sends us (with its title/year and, when available, an
`imdb://` / `tmdb://` external id) we resolve a Kinopoisk entry in tiers:

1. exact lookup by **IMDb id**, then by **TMDB id**;
2. fallback to **text search** by title, disambiguated by year, title similarity
   and media type.

The text fallback matters: Kinopoisk frequently lacks external ids even when it
has the title.

## Quick start (Docker Compose)

```bash
cp .env.example .env          # then edit POISKKINO_API_TOKEN
docker compose -f deploy/docker-compose.yml up -d
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/movie     # the movie provider manifest
```

The service binds to localhost only on the host — the provider API has **no
authentication yet**, so it must not be exposed to the internet.

### Register it in Plex

1. **Settings → Metadata Agents → Add Provider** and enter:
   - Movies: `http://127.0.0.1:8000/movie`
   - TV: `http://127.0.0.1:8000/tv`
2. Click **Add Agent**, name it (e.g. "Plex Movie + Kinopoisk"), and add the
   PoiskKino provider as a **secondary** source under *Plex Movie* / *Plex TV
   Series*, then order it below the primary.
3. In the library's **Advanced** settings select that agent, then refresh
   metadata.

See [docs/DEPLOY.md](docs/DEPLOY.md) for the systemd alternative, networking
notes, and troubleshooting.

## Configuration

All options are environment variables prefixed `POISKKINO_` (see
[`.env.example`](.env.example)). Key ones:

| Variable | Default | Description |
|----------|---------|-------------|
| `POISKKINO_API_TOKEN` | — | **Required.** Token from [@poiskkinodev_bot](https://t.me/poiskkinodev_bot). |
| `POISKKINO_RATING_IMAGE` | `kinopoisk` | How the KP score shows: `kinopoisk` (number + generic star, honest) or ride a branded icon (`imdb`/`themoviedb`/`rottentomatoes_ripe`/`rottentomatoes_upright`). |
| `POISKKINO_RATING_TYPE` | `critic` | Rating slot (`critic`/`audience`). `critic` is needed for the `kinopoisk` number to render. |
| `POISKKINO_WRITE_POSTER` | `true` | Contribute the Kinopoisk poster. |
| `POISKKINO_WRITE_SUMMARY` | `true` | Contribute the Russian description + tagline. |
| `POISKKINO_WRITE_ART` | `true` | Contribute background art. |
| `POISKKINO_WRITE_GENRES` | `false` | Contribute genres/countries. |
| `POISKKINO_MATCH_THRESHOLD` | `0.6` | Min title similarity (0–1) for a text‑search match. |
| `POISKKINO_PORT` | `8000` | HTTP port. |

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pre-commit install && pre-commit install --hook-type pre-push
ruff check . && mypy && pytest
uvicorn poiskkino_provider.app:create_app --factory --reload   # local dev server
```

Architecture: a framework‑free **core** (`poiskkino/` client + `matching/` +
`plex/mapping.py`) holds all the logic and is fully unit‑tested; the FastAPI
layer (`routes/`, `app.py`) is a thin adapter. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Releases

Versioned with [SemVer](https://semver.org/) and released automatically via
[Release Please](https://github.com/googleapis/release-please) from Conventional
Commits — merging the bot's release PR cuts a `vX.Y.Z` tag, a GitHub Release, and
the semver-tagged GHCR image (`latest` tracks the newest release, `edge` tracks
`master`). See [docs/RELEASING.md](docs/RELEASING.md).

## License

[MIT](LICENSE) © Pavel Sokolov
