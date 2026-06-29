# Deployment

The provider is a small HTTP service. Plex Media Server (**1.43.0+**) calls it
as a metadata source. It must be reachable by PMS but **not** by the public
internet (the Plex provider API has no authentication yet).

## Networking & security

- PMS and the provider talk over plain HTTP. Run the provider on the **same host
  as PMS** and let PMS reach it on `http://127.0.0.1:<port>`.
- The Docker Compose file binds the published port to `127.0.0.1` only; the
  systemd unit binds uvicorn to `127.0.0.1`. Do **not** expose the port on a
  public interface or behind a public reverse proxy until Plex ships provider
  authentication.
- Your PoiskKino API token lives only inside the service process (env var) and
  is never sent to Plex.

## Option A — Docker Compose (recommended)

```bash
cp .env.example .env            # set POISKKINO_API_TOKEN
docker compose -f deploy/docker-compose.yml up -d
docker compose -f deploy/docker-compose.yml logs -f
curl http://127.0.0.1:8000/health
```

Update to a newer image:

```bash
docker compose -f deploy/docker-compose.yml pull
docker compose -f deploy/docker-compose.yml up -d
```

To build locally instead of pulling from GHCR, edit `deploy/docker-compose.yml`
(comment out `image:`, uncomment the `build:` block) and run with `--build`.

## Option B — systemd (native, no Docker)

See the header of [`deploy/poiskkino-provider.service`](../deploy/poiskkino-provider.service)
for the full install recipe. In short: create a venv under
`/opt/poiskkino-provider`, `pip install` the package, drop your token into
`/etc/poiskkino-provider.env` (with `POISKKINO_HOST=127.0.0.1`), install the
unit and `systemctl enable --now poiskkino-provider`.

## Register the provider in Plex

1. **Settings → Metadata Agents → Add Provider** and add the base URL(s):
   - Movies: `http://127.0.0.1:8000/movie`
   - TV: `http://127.0.0.1:8000/tv`

   PMS reads the `MediaProvider` manifest from that URL. Each provider must be
   added separately because Plex recommends one parent media type per provider.
2. **Add Agent** — give it a name (e.g. "Plex Movie + Kinopoisk"). Add *Plex
   Movie* (or *Plex TV Series*) as the **primary** source and the PoiskKino
   provider as an **additional** source, then order PoiskKino **below** the
   primary so Plex keeps doing the matching and base metadata while PoiskKino
   contributes the Kinopoisk rating (and optionally the Russian poster/summary).
3. Open the library's **Edit → Advanced** tab, select the new Agent, save, and
   **Refresh All Metadata** (or refresh a single item to test).

## Verifying

- `GET /health` → `{"status":"ok"}`.
- `GET /movie` / `GET /tv` → the provider manifest JSON.
- Test a match without Plex:

  ```bash
  curl -s -X POST http://127.0.0.1:8000/movie/library/metadata/matches \
    -H 'Content-Type: application/json' \
    -d '{"type":1,"title":"Форсаж","year":2001,"guid":"imdb://tt0232500"}' | jq
  ```

## Troubleshooting

- **No Kinopoisk rating appears.** Confirm the PoiskKino provider is enabled and
  ordered in the library's Agent, then refresh metadata. Remember the rating
  shows under an IMDb/TMDb/RT icon (Plex has no Kinopoisk badge) — see the
  README.
- **`502` from the provider / empty matches.** Check the logs; a 401 means the
  token is wrong/empty, a 429 means the daily quota (5000 req/day) is exhausted.
- **Provider unreachable from PMS.** Ensure PMS and the provider are on the same
  host and the port matches; the service listens on `127.0.0.1` by design.
- **Wrong match via text fallback.** Raise `POISKKINO_MATCH_THRESHOLD` (e.g.
  `0.7`) to be stricter.
