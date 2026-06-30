# Release policy

This project uses **[Semantic Versioning](https://semver.org/)** and automates
releases with **[Release Please](https://github.com/googleapis/release-please)**,
driven by **[Conventional Commits](https://www.conventionalcommits.org/)**.

## How a version is decided

Release Please reads the commit messages merged into `master` and computes the
next version:

| Commit type | Example | Bump |
|-------------|---------|------|
| `fix:` | `fix: handle empty episode list` | patch (`0.1.0 → 0.1.1`) |
| `feat:` | `feat: add genres contribution` | minor (`0.1.0 → 0.2.0`) |
| `feat!:` / `fix!:` / `BREAKING CHANGE:` footer | `feat!: drop /tv endpoint` | major (`0.1.0 → 1.0.0`) |
| `chore:`, `docs:`, `refactor:`, `test:`, `ci:`, `perf:` | — | no release on their own |

(Pre-1.0, `feat` bumps the **minor** — `bump-minor-pre-major` is enabled.)

## The flow

1. You merge normal PRs into `master` with Conventional Commit messages.
2. The **Release Please** workflow keeps an open **"release PR"** that bumps the
   version in `pyproject.toml` + `src/poiskkino_provider/__init__.py` and updates
   `CHANGELOG.md` from the commits since the last release.
3. When you're ready to cut a release, **merge that release PR**. Release Please
   then creates the `vX.Y.Z` git tag and a **GitHub Release**, and the same
   workflow run builds and pushes the multi-arch image to GHCR.

You never tag or edit the version by hand.

## Image tags on GHCR

`ghcr.io/hacker-cb/plex-poiskkino-provider`:

| Tag | Tracks | Published by |
|-----|--------|--------------|
| `latest` | the newest release | Release Please workflow |
| `X.Y.Z`, `X.Y`, `X` | a specific release (e.g. `1.2.3`, `1.2`, `1`) | Release Please workflow |
| `edge` | the tip of `master` (unreleased) | Docker (edge) workflow |
| `sha-<commit>` | an exact commit | both workflows |

Pin to `X.Y` for automatic patch updates, or `X.Y.Z` for immutability. Use
`edge` only to test unreleased `master`.

## Overrides

- Force a specific next version: add `"release-as": "X.Y.Z"` to
  `release-please-config.json` for one release, then remove it.
- Keep a commit out of the changelog/release: don't use a release-triggering
  type (`feat`/`fix`), or mark it as `chore:`.
