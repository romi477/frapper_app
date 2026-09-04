# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Frapper is a personal language-learning pipeline. Polish (`pl`) and English (`en`) are supported. The author posts screenshots of phrases (a "target" phrase and its "translate" counterpart, e.g. from Reverso) into private Telegram channels. The system OCRs each screenshot, extracts the two phrases, and records **which words were highlighted** in the screenshot so they can later be retrieved and shown underlined / marked.

The grammatical construction being studied is highlighted light-yellow in the source image. Detecting that highlight is the core of the parsing logic: for every phrase the system stores a **word mask** — a string of `1`/`0` characters, one per word, where `1` marks a highlighted word. The bot rebuilds highlights as `<u>`; the web UI uses amber `<mark>`.

Separately, the web UI supports **English study texts** (`text_en`, UI label **Stories**): longer dialogue or reading passages stored as title + body + semicolon-separated tags. Bodies may be plain text (newlines preserved) or HTML fragments in a `<div class="window">` dialogue format (styled like a macOS window with `.key` highlight spans).

## Architecture

Everything runs as Docker Compose services at the repo root (`compose.yaml`). There is no orchestration code beyond compose; app services communicate only through Redis and HTTP on the internal Compose network.

```
Telegram channel(s) ──> bot ──(image bytes)──> Redis ──> listener ──(OCR + parse)──> API ──> SQLite
        ^                                                                                    |
        └──────────────── Telegram client queries (bot command handlers) ────────────────────┘
                                                                                             |
                         host Nginx (TLS) ──> 127.0.0.1:<FRAPPER_API_PORT> (api, loopback only) ───┘
                                                                                             |
                                                    web frontend (GET /web, Basic Auth)
                                                    manual phrase/story CRUD (web only)
```

- **`api/`** — FastAPI + Pony ORM over SQLite. The only stateful store. Persists `phrase_meta`, `phrase_pl`, `phrase_en`, and `text_en`; exposes lang-aware phrase endpoints plus English text endpoints. Serves a single-page web frontend at `GET /web` (Basic Auth); `GET /` redirects to `/web`. Entry point `python -m app` runs `ensure_db` then uvicorn on `0.0.0.0:${FRAPPER_API_PORT}` **without** reload. The **only** published port is `127.0.0.1:${FRAPPER_API_PORT}` so host Nginx can proxy it; redis/bot/listener are not published.
- **`bot/`** — Telethon bot. Two roles: (1) listens to phrase channels (`TG_PHRASE_PL_ID`, optional `TG_PHRASE_EN_ID`), and on every new **photo** message POSTs a `phrase_meta` row to the API, then stores the raw image bytes in Redis; (2) handles slash-command messages from the Telegram client to query phrases back via the API. Entry point `python -m app.bot`. Session files live in `bot/data/` (`/opt/bot/data` in the container).
- **`listener/`** — Polling worker (no web server). Every 5s it scans all Redis keys, parses each stored image, and POSTs the extracted phrases to the API. Entry point `python -m app.listener`.
- **`redis/`** — message/work queue between bot and listener. DB 0 holds pending images; failed/unparseable items are `MOVE`d to **DB 1** for later inspection (never lost, never retried automatically). Not published; capped `--maxmemory`.
- **`core/frapper_core/`** — installable shared package (UV workspace member `frapper-core`). Used by bot, listener, and API. Built into each image via `uv sync` (not bind-mounted in compose). Holds Redis key helpers, Pydantic wire schemas, HTTP client, `api_base_url()`, mask rebuild, and `FrapperConfig` pixel constants. Compose build context is the repo root.

Internal API URL is `http://${FRAPPER_API_HOST}:${FRAPPER_API_PORT}` (compose: `api` + `FRAPPER_API_PORT`). Change **only** `.env`; do not hardcode the port in app code.

### Data flow details

- **Redis key format** (`core/frapper_core/redis_keys.py`): `"{lang}_{message_id}_{message_date}"`, split with `maxsplit=2` because the ISO date itself contains no underscores. The value is the raw downloaded image bytes. The bot derives `lang` from which Telegram channel received the photo (`phrase_channels()` map in `bot/app/bot.py`).
- The listener parses the key → gets `lang`, looks up `meta_id` via `GET /api/phrase-meta?lang=&message_id=&datetime_created=`, then POSTs parsed rows to `POST /api/phrase?lang=`.
- The listener splits **one screenshot into possibly several phrase records** — a single image may stack multiple phrase rows. `ImageFrapper.split_image_from_bin_data` finds the horizontal separator stripes and yields one `ImageFrapper` per phrase block.
- Each `ImageFrapper` then splits its block into a **target** row and a **translate** row (`split_row_image` via `find_split_height`), OCRs both, and computes the highlight mask.
- Only records where `is_done` is true (state `done` plus all four text fields populated) are POSTed. If a key produces no valid records, it is moved to Redis DB 1.

### Image parsing internals (`listener/app/frapper.py`, `listener/app/tools.py`)

This is the most subtle part of the codebase and depends on hard-coded pixel geometry tuned to Reverso screenshots. Constants live in `FrapperConfig` (`core/frapper_core/constants.py`):

- Images are normalized to `STANDARD_WIDTH = 1080`; offsets (`IMAGE_OFFSET_L/R`, `CUT_THE_ARROW_OFFSET`) crop margins and the arrow glyph between rows. Changing the source image layout will break these.
- **Row/phrase separation** relies on detecting fully-white separator pixel columns/rows. The background pixel sum changed when Reverso redesigned: `PIXEL_SUM_V1` (255×3) before `2023-05-10`, `PIXEL_SUM_V2` (243+247+250) after. `get_pixel_sum` picks the right one from `message_date`, so the message date is load-bearing, not just metadata.
- **Highlight detection** (`_is_tag` + `in_a_range`): for each OCR word box it samples a pixel row just above the word (`TAG_OFFSET`) and counts pixels falling in the light-yellow RGB ranges (`R_RANGE`, `G_RANGE`, `B_RANGE`). If ≥ `THRES_HOLD_TAG`% match, the word is tagged → mask `1`. The concatenation of per-word `1`/`0` is `target_mask` / `translate_mask`. The tagged words joined together form `target_tag` / `translate_tag` (the searchable "construction").
- OCR uses **pyocr + Tesseract** with `lang='pol'` (the `tesseract-ocr-pol` apt package is installed only in the listener Dockerfile). The same OCR language is used for EN-channel screenshots as well. `to_gray` binarizes to pure black/white at `THRES_HOLD_BLACK`.

### API model (`api/app/`)

- **Pony ORM**, not SQLAlchemy. Models in `models/`, bound to SQLite in `db/database.py` with `create_db=False`, mapping generated in `models/__init__.py` with `create_tables=False` — **the schema is expected to already exist** (API startup runs `ensure_db` / `migrate_db.py` to create or migrate). Pony requires every DB function to run inside `@db_session`.
- `phrase_meta` — one row per incoming Telegram photo message. `composite_key(lang, message_id, datetime_created)`. Fields: `lang`, `message_id`, `datetime_created`, `with_error`, `created_at`. **No `state` column** on meta. Channel IDs are not stored (channels are bot-only config).
- `phrase_pl` / `phrase_en` — one row per parsed phrase per language table, FK `meta_id` → `phrase_meta` (nullable for manual web creates), `composite_key(target, target_tag)` to dedupe. Language is implied by the table name (no `lang` column on phrase rows). Carries `target`/`translate` text, their `_tag` and `_mask`, `state`, and `active` (only `active=true` rows are served).
- `text_en` — English study texts / Stories, independent of phrase OCR. Fields: `title`, `body`, `tags` (semicolon-separated keywords), `created_at`, `updated_at`. No lang column (English-only table). Tags must be `Optional(str, default='')` in Pony — `Required(str)` rejects empty strings and causes 500s on create/update.
- Query logic for phrases is shared in `app/services/phrase.py`; `app/lang.py` maps `lang` query param → Pony entity (`PhrasePl` or `PhraseEn`). Text logic lives in `app/services/text_en.py` with body normalization in `app/services/text_body.py`.
- All phrase routes live at **`/api/phrase?lang=pl|en`** (required except stats). Legacy `/api/phrase-pl` routes are removed.
- Text routes live at **`/api/text-en`** (no lang param — English only).
- Phrase-meta routes: `GET`/`POST` **`/api/phrase-meta?lang=`**.
- FastAPI's interactive docs are **off by default** (`FRAPPER_ENABLE_DOCS=false`). Set `true` in `.env` to expose `/docs`, `/redoc`, `/openapi.json`. Those routes use the same HTTP Basic auth as the web UI and API (`FRAPPER_USERNAME` / `FRAPPER_PASSWORD` via `validate_basic`). Built-in unauthenticated FastAPI docs URLs are disabled. All API endpoints and `GET /web` use the same `validate_basic`.
- Read endpoints build SQL with f-strings and `select_by_sql` (note: `target-tag`/`translate-tag` interpolate the user `tag` directly — be careful if hardening).
- `GET /health` — unauthenticated DB probe used by the compose healthcheck.

### Phrase API endpoints (`api/app/api/phrase.py`)

| Method | Path | Meaning |
|---|---|---|
| `POST` | `/api/phrase?lang=` | Bulk insert from listener (list of `PhraseSchema`) |
| `POST` | `/api/phrase/manual?lang=` | Create one phrase from web UI (`PhraseUpdate` body) |
| `GET` | `/api/phrase/target-tag?lang=&tag=` | By construction tag (random tag if omitted) |
| `GET` | `/api/phrase/translate-tag?lang=&tag=` | By translate-side construction |
| `GET` | `/api/phrase/fetch-count?lang=&count=` | Random active phrases (default count 10) |
| `GET` | `/api/phrase/fetch-slice?lang=&since_id=&count=` | Phrases with `id >= since_id` |
| `GET` | `/api/phrase/fetch-tail?lang=&tail=&count=` | Random from last `tail` rows (defaults tail=100, count=10) |
| `GET` | `/api/phrase/fetch-date?lang=&date=` | Phrases whose `message_date` falls on ISO date |
| `GET` | `/api/phrase/date-count?lang=&date=` | Count available for a date (`{count}`) |
| `GET` | `/api/phrase/stats` | Active phrase counts and max ids per lang (`pl`, `en`) |
| `GET` | `/api/phrase/{id}?lang=` | Single phrase by id |
| `PATCH` | `/api/phrase/{id}?lang=` | Update target/translate/masks |
| `DELETE` | `/api/phrase/{id}?lang=` | Delete by id |

Tag search uses `LIKE '%tag%'` for queries ≥ 4 chars, exact match otherwise. A trailing `==` (e.g. `tag==`) forces an exact match on the stripped tag, regardless of length. The same rules apply to `text_en` tag search in `text_en.py`.

Manual phrase create (`POST /manual`) sets `meta_id=None`, `state='done'`, `active=True`, derives `target_tag`/`translate_tag` from the masks, and uses `message_id=0` with `message_date=now`.

### Text EN API endpoints (`api/app/api/text_en.py`)

| Method | Path | Meaning |
|---|---|---|
| `POST` | `/api/text-en` | Create text (`TextEnCreate`: title, body, tags) |
| `GET` | `/api/text-en?tag=` | List summaries `{id, title, tags, created_at}` (newest first) |
| `GET` | `/api/text-en/{id}` | Full record including body |
| `PATCH` | `/api/text-en/{id}` | Partial update (at least one field required) |
| `DELETE` | `/api/text-en/{id}` | Delete by id |

All write paths run `prepare_text_body()` before persisting. Validation errors return HTTP 422 with a string `detail`.

### Text body processing (`api/app/services/text_body.py`)

Shared normalization/validation used by the API; the web UI mirrors the same rules client-side before save/upload.

- **Plain text** — stored as-is; newlines preserved. Display uses `textContent` + `white-space: pre-wrap`.
- **HTML upload** — if input looks like HTML, tries to extract a single outer `<div class="window">…</div>` fragment; otherwise converts HTML to plain text.
- **Stored HTML** — after normalization, HTML bodies must be exactly one `<div class="window">` root element.
- **Forbidden content** — `<script>`, `<style>`, `<iframe>`, `<object>`, `<embed>`, `<link>`, `javascript:` URLs, inline `on*` event handlers.
- Tags are normalized to semicolon-separated unique tokens (`office;dialogue`).

### Wire schemas (`core/frapper_core/schemas.py`)

Shared Pydantic models used across services:

| Class | Role |
|---|---|
| `PhraseMetaCreate` / `PhraseMetaSchema` | POST body for phrase-meta |
| `PhraseCreate` / `PhraseSchema` | POST body for phrase rows |
| `PhraseResponse` / `PhraseList` | GET response validation (bot) |
| `PhraseUpdate` | Manual create / PATCH body (target, translate, masks) |

`api/app/schemas/` re-exports phrase schemas and defines text schemas locally (`text_en_schema.py`: `TextEnCreate`, `TextEnUpdate`, `TextEnSummary`, `TextEnResponse`).

### Bot command surface (`bot/app/bot.py`)

Commands are sent by the Telegram client to the bot; each maps to an API call and renders results as HTML with highlighted words wrapped in `<u>` (rebuilt from the mask via `frapper_core.rebuild_string`):

| Command | Endpoint | Meaning |
|---|---|---|
| `/c [n]` | `fetch-count` | `n` random active phrases (default 4) |
| `/s <since_id> <n>` | `fetch-slice` | `n` phrases with `id > since_id` |
| `/l [tail] [n]` | `fetch-tail` | `n` random phrases from the last `tail` rows |
| `/f [tag]` | `target-tag` | phrases by construction tag (random if no tag) |
| `/t [tag]` | `translate-tag` | phrases by translate-side construction |
| `/d <id>` | `DELETE /phrase/{id}` | delete by id — **super-user (`TG_SU_ID`) only** |
| `/start` | — | greeting |

**Note:** slash-command handlers currently hardcode `lang='pl'` for API calls. Only the photo-ingest handler uses the channel → lang map.

**Channel IDs:** `TG_PHRASE_PL_ID` / `TG_PHRASE_EN_ID` should be the **short** channel id (numeric part only, without the `-100` prefix). The ingest handler strips `-100` from Telethon's `event.chat_id` before lookup.

### Web frontend (`api/app/static/index.html`)

Single-page UI at `GET /web` (Basic Auth). `GET /` redirects here. All logic is inline in one HTML file (CSS + JS, no build step).

#### Shell and chrome

- Outer page background `#e6e8ed`; main UI sits in **`#app-shell`** — near-white polished silver (`#f7f8fa`) with subtle grain, inset padding, rounded border, soft shadow.
- **Header chrome links** (quiet text, no cards/shadow/z-index): language (`localStorage` `frapper.lang`) · Reset all canvases · Logout (invalid Basic Auth re-fetch). Live in the header body and hide when the header is collapsed.
- **Header theme** — muted dusty violet for PL (`#5e598a`), azure blue for EN (`#46769f`). Header + canvas share `--header-bg`.
- Header is collapsible (`frapper.headerCollapsed`).
- Brand: clickable `FRAPPER` → GitHub repo; hover shows phrase stats tooltip; version badge → `/docs` (Swagger, needs `FRAPPER_ENABLE_DOCS=true`). Subtitle + phrase stats via `GET /api/phrase/stats`.
- Tab toolbar (right): **+ Item** (`Ctrl+I`), then dedupe, badges, card count.

#### Query modes

Modes are grouped: **phrase** (Tag, Tail, Count, Slice, Date) and **text** (**Stories**), each with an underline label under the pill row.

| Mode | Endpoint | Input |
|---|---|---|
| Tag | `target-tag` | Construction tag, or empty for random |
| Tail | `fetch-tail` | `count`, or `tail:count` (e.g. `200:10`) |
| Count | `fetch-count` | Optional count |
| Slice | `fetch-slice` | `since_id`, or `since_id:count` |
| Date | `fetch-date` | ISO date (`YYYY-MM-DD`); prev/next day buttons; prefetches count via `date-count` and shows it on the Enter button |
| Stories | `GET /api/text-en` | Tag keyword, or empty for all — **EN language only** |
| ID | `GET /api/phrase/{id}` | Phrase id — visible only with `?debug=1` |

Press Enter or the ↵ button to run. **+ Item** opens create modal: phrase dialog in phrase modes, story dialog in Stories mode.

When language is PL, the Stories pill is visible but disabled (`is-disabled`); switching to PL while in Stories auto-falls back to Tag.

#### Canvases (results)

- Always **4 fixed canvases** (`MAX_TABS = 4`), bootstrapped on load — not user-created closable tabs.
- Horizontal **carousel**: panels sit in a row (`#tab-panels`); switching slides with `translate3d` (~0.38s). Inactive panels are hidden after settle so neighbors do not peek while scrolling.
- Center of the tab toolbar: **4 thick line indicators** (`.tab-dot`) — horizontal bars, larger hit target than round dots.
- Touch swipe left/right also switches canvases.
- **Switching canvas calls `setMode('tag')`** — Tag pill active, query cleared, focus in the input (fresh construction search on the new canvas).
- Global **Reset** header link rebuilds all four empty canvases.

#### Tab toolbar (active canvas)

| Side | Actions |
|---|---|
| Left | Clear tab · Collapse all · Expand all · Shuffle |
| Right | **+ Item** (`Ctrl+I`) · Dedupe (“Keep unique cards”) · Badges modal · card count |

- **Dedupe** — phrases by id + construction tag; stories by id + tags (title fallback).
- **Badges** — compact modal of unique construction/tags in the active canvas, with Copy.
- Shuffle prepends a “Shuffled · N” batch label.

#### Phrase cards

- Dense layout (tight padding, ~17px target / ~15px translate, short head→body gap).
- Amber `<mark>` highlights from mask.
- Language-specific tag badge colors (muted PL violet / EN blue); badges are visually quiet (small, light fill).
- Header: collapse, `#id`, message date (click → Date mode), edit, delete.
- Construction tag button → Tag mode search.
- **Edit** — FLIP morph to phrase edit modal; click words to toggle mask bits; `PATCH` or `POST /manual` for create.
- **Delete** — confirm modal; `DELETE /api/phrase/{id}`.
- **YouGlish** — on EN phrase target line only: ⌘ + double-click a single selected word opens an embedded pronunciation modal (plus “Open on YouGlish” link).

#### Story cards (`text_en`)

- Summary from `GET /api/text-en` (title + tags). Title click lazy-fetches `GET /api/text-en/{id}`.
- Full body: HTML dialogue (`.window`, `.key`) or plain text (`pre-wrap`).
- Tag buttons → Stories mode search for that tag.
- Edit disabled until full body is loaded; then `PATCH`/`DELETE` on `/api/text-en/{id}`.
- **Upload from disk** in create/edit modal: `.txt` / `.html`; client + server validate via the same rules as `text_body.py`.

#### Dialogs / animations

- Phrase and story create/edit modals and badges/delete dialogs use compact padding and small action buttons.
- Card ↔ dialog transitions use FLIP-style morph (`morphBetweenCardAndDialog`). Keep `is-morphing` for the full animation (including when `skipModalInit` is true) to avoid a duplicate dialog flash.
- `prefers-reduced-motion` disables carousel slide and morph transitions.

## Running

All commands run from the **repo root**. Copy `.env.example` to `.env` and fill in the values before starting.

Required `.env` keys: Telegram API id/hash, bot token, channel/user ids, Redis host/port, `FRAPPER_API_HOST` (Docker DNS name, e.g. `api`), `FRAPPER_API_PORT`, Basic Auth credentials, `SQLITE_DB_PATH`.

```bash
# Build and run the whole stack
docker compose up --build -d

# Run / rebuild a single service
docker compose up --build listener
docker compose logs -f bot
# or: ./scripts/docker-logs.sh bot

# Open a Pony ORM shell against the API DB (inside the api container)
# Loads pony.orm *, config, db, PhraseMeta as M, PhrasePl as P
docker compose run --rm api python -i app/shell.py
```

### Database

- Compose bind-mounts `./_frapper.db` → `/opt/api/frapper.db`.
- `SQLITE_DB_PATH` is defined in `.env` (e.g. `frapper.db`). The API reads it via `api/app/config.py` (pydantic-settings, also loads `.env` for local runs). Relative paths resolve against the API root (`/opt/api` in the container).
- Schema changes: run `python3 api/migrate_db.py _frapper.db` (idempotent). API startup also runs `ensure_db` (create empty schema if missing, migrate if present).

The only host-facing port is `127.0.0.1:${FRAPPER_API_PORT}` on the api service (for host Nginx). Service logs go to stdout (Docker `json-file` driver, `max-size`/`max-file` rotation — no `./logs` bind-mount). The bot Telethon session is `bot/data/frapper-bot.session` (gitignored). Images copy `core` at build time (not a live bind-mount).

## Notes / gotchas

- **There are no tests, no linter config, and no CI** in this repo. Don't claim a change is verified by tests that don't exist.
- Each service has a `pyproject.toml`; the repo root is a UV workspace with one `uv.lock` (`requires-python = ">=3.11,<3.12"`). Dockerfiles use `uv sync --locked` on `python:3.11-slim-bookworm`. The listener is the only image needing Tesseract/Pillow/NumPy.
- Pony is pinned at **0.7.19** in `api/pyproject.toml`. Entity fields must be declared directly on entity classes — a shared Pony mixin was tried and failed to register columns. Use `Optional(str, default='')` for nullable-in-practice string fields like `TextEn.tags`.
- `_frapper.db` is the working database file (bind-mounted, not necessarily committed). There is no ORM migration framework beyond `api/migrate_db.py` / `ensure_db`.
- Pixel-geometry constants in `FrapperConfig` are coupled to the exact Reverso screenshot layout; treat them as calibration, and re-derive them if the source image format changes (rather than guessing).
- Old Redis keys in the `{meta_id}_{message_id}_{date}` format will not parse — flush Redis DB 0 if upgrading from a pre-multilang deployment.
- Text body validation is duplicated in `text_body.py` (server) and `index.html` (client) — keep them in sync when changing rules.
- HTML text bodies are rendered with `innerHTML` in the card view; the validation layer is the security boundary (no scripts/styles/iframes).
- Bot query commands hardcode `lang='pl'`; OCR always uses Tesseract `pol`, including for EN-channel screenshots.
- Web UI result area is **4 fixed canvases + carousel**, not closable multi-tabs. Canvas switch resets query mode to Tag.
