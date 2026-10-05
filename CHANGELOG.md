# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] — 2026-10-05

Bug-fix release from a full code review.

### Security

- Phrase tag search (`/api/phrase/target-tag`, `/translate-tag`) no longer interpolates the tag into raw SQL: it is a bound parameter. Before, an authenticated request could run SQL and, through Pony's `$expr` evaluation in raw SQL, arbitrary Python in the API process
- Story HTML is re-serialized through an allowlist sanitizer on the server (`sanitize_html`) and in the web UI (on save and on render). The old regex blacklist let entity-encoded `javascript:` links, `<meta refresh>`, `<base>` and similar through

### Fixed

#### API

- `python -m app` now runs `ensure_db` before the models bind and check the database: a missing, empty or outdated SQLite file no longer crash-loops the API
- Tags with an apostrophe (e.g. `don't`) no longer return 500; `%` and `_` in a tag are matched literally
- `POST /api/phrase` skips phrases that already exist (or repeat within the batch) instead of rejecting the whole screenshot with 409
- `fetch-tail` serves only active phrases and takes the last `tail` rows by id (deleted ids no longer widen the pool)
- `DELETE /api/phrase/{id}` returns 404 for a missing phrase
- `POST /api/phrase-meta` is idempotent for the same message; a malformed `datetime_created` returns 422 instead of 500
- HTML stories keep the closing `>` of the root `</div>`; a migration step repairs bodies saved without it
- Plain-text stories containing `<` without a later `>` (e.g. `a<b`) are no longer truncated, and text after a trailing `&` is kept

#### Listener

- One failing screenshot no longer crashes the worker: it is parked in Redis DB 1; an unreachable API leaves the key queued for the next pass
- A key that already exists in DB 1 is replaced instead of being re-processed every 5 seconds
- Each phrase block of a screenshot keeps its own `metadata` (size, position, thresholds)
- Highlight sampling no longer wraps to the bottom row for words at the top edge or divides by zero on zero-width boxes

#### Bot

- `/l <tail>` works (it raised `IndexError`); `/l` and `/s` no longer match unrelated or over-long commands
- `/d` of a missing id replies "Not Found" instead of "OK"
- API and Redis calls run off the event loop with timeouts; failures are reported in the chat instead of freezing the bot or failing silently

#### Web UI

- Results fetched before a language switch keep their language, so edit/delete hit the right table
- "Today" in Date mode uses the local date (it was UTC)
- Deleting a phrase that is already gone removes the card instead of showing an error

### Changed

- The SQLite database lives in `data/` (`SQLITE_DB_PATH=data/frapper.db`); Compose mounts the directory and requires `SQLITE_DB_PATH`
- Redis persists the queue (AOF on the `redis-data` volume) and uses `noeviction` instead of `allkeys-lru`
- HTTP calls from the bot and listener (`FrapperApiClient`) time out after 30 seconds
- Removed the unused `TG_FRAPPER_ID` setting

### Added

- Pytest suites for `core`, `api`, `bot` and `listener`, run with `./scripts/run-tests.sh`

## [1.0.0] — 2026-09-04

Initial release of Frapper.

### Added

#### Pipeline

- Telegram ingest of Reverso-style phrase screenshots (Polish and English channels)
- OCR listener with highlight detection → word masks and construction tags
- Redis work queue between bot and listener (failed jobs retained in a separate DB)
- Shared `frapper_core` package (schemas, Redis keys, API client, mask rebuild, OCR constants)
- SQLite persistence via FastAPI + Pony ORM (`phrase_meta`, `phrase_pl`, `phrase_en`, `text_en`)

#### API

- Phrase endpoints: create (bulk + manual), fetch by tag / count / slice / tail / date / id, stats, update, delete
- Phrase-meta create and lookup for Telegram message correlation
- English Stories (`text_en`): create, list (optional tag filter), get, update, delete
- Text body normalization (plain text or single `<div class="window">` HTML dialogue)
- HTTP Basic Auth on API, web UI, and optional Swagger/ReDoc (`/docs`, `/redoc`, `/openapi.json`)
- Unauthenticated `/health` probe for Compose
- Tag search rules: substring for longer tags, exact match otherwise, trailing `==` for forced exact

#### Telegram bot

- Photo ingest into the phrase pipeline
- Commands: `/c`, `/s`, `/l`, `/f`, `/t`, `/d` (super-user), `/start`
- Highlighted phrase replies rebuilt from word masks

#### Web UI (`/web`)

- Single-page app with PL / EN language switch
- Query modes: Tag, Tail, Count, Slice, Date (with day navigation and count prefetch), Stories (EN only), debug ID
- Four fixed result canvases with horizontal carousel and line indicators
- Canvas toolbar: clear, collapse/expand all, shuffle, add item, dedupe, badges list (with copy), card count
- Canvas switch resets to Tag mode for a fresh construction search
- Phrase cards with mask highlights, edit/delete, collapse, date → Date mode, tag → Tag mode
- Story cards with lazy body load, HTML or plain text, tags, upload from disk, edit/delete
- Create/edit dialogs for phrases (click-to-toggle mask) and Stories
- YouGlish pronunciation (⌘ + double-click a word on an EN phrase target)
- Collapsible header, silver app shell, muted PL / azure EN themes
- Header chrome links (language, Reset, Logout); brand → GitHub; version badge → Swagger
- Card ↔ dialog morph animations; keyboard shortcuts; Logout via Basic Auth clear

#### Docs & tooling

- `README.md`, `CLAUDE.md`, Docker Compose stack (`compose.yaml`)
- UV workspace with locked dependencies (`pyproject.toml` / `uv.lock`)
- DB `ensure_db` / `migrate_db.py`, fixture loader, `scripts/docker-logs.sh`

[1.0.1]: https://github.com/romi477/frapper_app/releases/tag/v1.0.1
[1.0.0]: https://github.com/romi477/frapper_app/releases/tag/v1.0.0
