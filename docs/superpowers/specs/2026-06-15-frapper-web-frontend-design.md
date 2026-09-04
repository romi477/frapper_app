# Frapper Web Frontend — Design

Date: 2026-06-15
Status: Approved (pre-implementation)

## Purpose

Add a small web frontend to the `api` service that lets the author query parsed
Polish phrases through three of the existing `/api/phrase-pl` read endpoints,
rendering each phrase with its highlighted words (rebuilt from the stored word
masks). As part of this work, the API's authentication is migrated from a Bearer
token to HTTP Basic Auth across all services.

## Scope

In scope:

- A single static page served by the `api` service.
- Three query modes: Count, Tail, Tag.
- Highlighted rendering of returned phrases.
- Session-scoped, accumulating result history with a Clear control.
- Replacing Bearer-token auth with HTTP Basic Auth in `api`, `bot`, and `listener`.

Out of scope:

- Write/delete operations from the frontend (read-only UI).
- The `fetch-slice` and `translate-tag` endpoints (not requested).
- Persisting history across page reloads.
- Any automated tests or CI (the repo has none; verification is manual).

## Architecture & components

- **Serving:** one self-contained `api/app/static/index.html` (inline CSS +
  vanilla JS, no build step). Served by the existing FastAPI `api` service. No
  new container, no CORS.
- **Data flow:** the page calls the existing `/api/phrase-pl/*` endpoints with
  `fetch()`. All session state (current mode, accumulated history) lives in the
  browser; nothing new is persisted server-side.
- **Access:** the API is published only on `127.0.0.1:4040`, so the page is
  reachable at `http://127.0.0.1:4040/`.

## Authentication migration (Bearer → Basic)

The frontend and the API share one origin and one Basic Auth realm. Opening the
page triggers the browser's native Basic login dialog once; the browser then
auto-attaches the credentials to every same-origin `/api/*` request, so the JS
needs no token handling or custom login form.

- `api/app/utils.py`: replace `validate_bearer` (`HTTPBearer`) with
  `validate_basic` (`HTTPBasic`). Validate the supplied username/password against
  `API_DOCS_USERNAME` / `API_DOCS_PASSWORD` using `secrets.compare_digest`
  (constant-time comparison). On failure, return `401` with a
  `WWW-Authenticate: Basic` header (the default for `HTTPBasic(auto_error=True)`).
- Swap `Depends(validate_bearer)` → `Depends(validate_basic)` in
  `api/app/api/phrase_pl.py` and `api/app/api/phrase_meta.py`.
- Add a page route: `GET /` → returns `index.html`, protected by
  `Depends(validate_basic)` so a top-level visit forces authentication before the
  page (and therefore its API calls) can run.
- `bot/app/bot.py` and `listener/app/listener.py`: remove the `Bearer` header and
  authenticate with Basic instead (`requests` `auth=(user, password)`).
- `bot/app/config.py`: add `api_docs_username` / `api_docs_password`. The listener
  reads them via `os.getenv` (consistent with its current style).
- Remove `frapper_api_bearer_token` from `api`, `bot`, and `listener` config and
  from environment wiring.
- `docker-compose.yml`: add `API_DOCS_USERNAME` / `API_DOCS_PASSWORD` to the `bot`
  and `listener` services; drop the `FRAPPER_API_BEARER_TOKEN` entries. The `api`
  service already receives `API_DOCS_USERNAME` / `API_DOCS_PASSWORD`.
- `.env.example`: drop `FRAPPER_API_BEARER_TOKEN`; keep `API_DOCS_USERNAME` /
  `API_DOCS_PASSWORD` as the now-active credentials.

## Modes

Header shows three mode pills: **Count / Tail / Tag**. There is a single input
line; pressing **Enter** runs the request for the active mode. Switching modes
updates the input placeholder and clears the input.

| Mode  | Endpoint                  | Input                         | Empty input behavior            |
|-------|---------------------------|-------------------------------|---------------------------------|
| Count | `GET /fetch-count`        | one number → `count`          | omit `count` → API default (4)  |
| Tail  | `GET /fetch-tail`         | one number → `tail`; `count` fixed at 10 | omit params → API defaults |
| Tag   | `GET /target-tag`         | text → `tag`                  | omit `tag` → server returns a random construction |

## Rendering

For each returned record, the target and translate strings are rebuilt exactly
like the bot's `_rebuild_string`: split the sentence on whitespace, and for word
*i* wrap it in a highlight `<span>` when `mask[i] == '1'`. Each record renders as
a card matching the approved light-theme mockup:

- ID badge (`#<id>`, the `#` in the amber accent color).
- Target sentence on top (regular weight).
- Translate sentence below, muted and italic.
- Highlighted words use a translucent yellow background (no underline).

Layout: a centered single column (max-width ~680px), light theme, sticky header
containing the brand, the mode pills, and the input row with an "↵ Enter" hint.

## Session history & Clear

- Each successful request **prepends** its batch to the top of the results
  container: a thin batch-label separator (e.g. `Count · 6 · just now`) followed
  by that request's cards.
- History accumulates across requests for the lifetime of the page (in-memory
  only; a reload starts empty).
- A floating **Clear** button pinned to the top-right corner empties the results
  container.

## Loader & error handling

- On submit: show a centered spinner, perform the `fetch`, and enforce a
  **minimum display time of ~1s** so the loader is always visibly shown, then
  prepend the results.
- Empty result set → a small "Not found" batch.
- Network or non-OK HTTP response → a small inline error batch (red text).
- `401` is handled by the browser's native Basic Auth dialog.

## Testing / verification

The repository has no tests, linter config, or CI, so verification is manual:

1. `docker compose up --build`.
2. Open `http://127.0.0.1:4040/` and authenticate via the browser Basic dialog.
3. Exercise each mode (Count, Tail, Tag with and without a tag), pressing Enter
   to run.
4. Confirm highlighting matches the masks, results accumulate newest-on-top,
   Clear empties the list, and the loader shows for ~1s.
5. Confirm the bot and listener still reach the API using Basic Auth.

No automated-test coverage is claimed.
