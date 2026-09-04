# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.0]: https://github.com/romi477/frapper_app/releases/tag/v1.0.0
