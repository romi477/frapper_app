# Frapper

Personal language-learning pipeline for **Polish** and **English** phrases — plus longer English **Stories**.

You post Reverso-style screenshots into private Telegram channels. Frapper OCRs them, extracts the target/translate pair, and remembers which words were yellow-highlighted so you can search by construction and review with the same highlights.

## What it does

- **Ingest** — Telegram photo → OCR → SQLite phrases (`pl` / `en`) with word masks
- **Bot** — slash commands to fetch random / tagged / sliced phrases in Telegram
- **Web UI** — Basic-auth SPA at `http://127.0.0.1:<FRAPPER_API_PORT>/web` (localhost only; proxy from host Nginx)

## Stack

| Service | Role |
|---|---|
| `api` | FastAPI + SQLite; only published bind is `127.0.0.1:<FRAPPER_API_PORT>` |
| `bot` | Telethon ingest + commands |
| `listener` | Redis worker: OCR with Tesseract, POST phrases |
| `redis` | Image queue (pending in DB 0; failures moved to DB 1; AOF-persisted, `noeviction`) |

Shared code lives in `core/frapper_core/`.

```
Telegram ──> bot ──> Redis ──> listener ──> API ──> SQLite
                └──── slash commands ────┘      ▲
                                                │
                          host Nginx (TLS) ──> 127.0.0.1:<FRAPPER_API_PORT> ──> api
```

## Quick start

1. Copy env and fill in values:

```bash
cp .env.example .env
```

Typical compose values:

```env
FRAPPER_API_HOST=api
FRAPPER_API_PORT=4040
FRAPPER_ENABLE_DOCS=false
REDIS_HOST=redis
REDIS_PORT=6379
SQLITE_DB_PATH=data/frapper.db
```

`FRAPPER_API_HOST` is the Docker DNS name of the API service (not a URL). `FRAPPER_API_PORT` is the one port to change: uvicorn, internal clients, and the localhost publish (`127.0.0.1:<port>`). Host Nginx / TLS should proxy to that loopback port; do not publish `api` or `redis` to `0.0.0.0`.

Also set Telegram API id/hash, bot token, channel ids (`TG_PHRASE_PL_ID`, optional `TG_PHRASE_EN_ID` — short numeric ids, without `-100`), super-user id, and Basic Auth (`FRAPPER_USERNAME` / `FRAPPER_PASSWORD`).

2. Create the bind-mounted directories (the API creates `data/frapper.db` via `ensure_db` on first start):

```bash
mkdir -p data bot/data
```

3. Start the stack:

```bash
docker compose up --build -d
```

Web UI: `http://127.0.0.1:4040/web` (or whatever `FRAPPER_API_PORT` is). Basic Auth. On the server, proxy this loopback port from host Nginx.

```bash
# one service / logs
docker compose up --build listener
./scripts/docker-logs.sh bot
# or: docker compose logs -f bot

# Pony shell (PhraseMeta as M, PhrasePl as P)
docker compose run --rm api python -i app/shell.py

# manual migration
python3 api/migrate_db.py data/frapper.db

# tests (pytest per service via uv)
./scripts/run-tests.sh
```

## Web UI

- **Languages** — PL / EN (Stories only in EN)
- **Modes** — Tag, Tail, Count, Slice, Date, Stories (`?debug=1` also shows ID)
- **Canvases** — four fixed result boards; switch with the line indicators or swipe; switching resets to Tag
- **Toolbar** — clear, collapse/expand all, shuffle, add item, dedupe, badge list
- **Cards** — edit/delete phrases and Stories; mask highlights on phrases; lazy-load Story bodies; upload `.txt` / `.html` for Stories
- **YouGlish** — on an EN phrase target line: ⌘ + double-click a selected word

## Bot commands

Handled in Telegram (API calls currently use `lang=pl`):

| Command | Meaning |
|---|---|
| `/c [n]` | `n` random phrases (default 4) |
| `/s <since_id> <n>` | slice by id |
| `/l [tail] [n]` | random from last `tail` rows |
| `/f [tag]` | by target construction tag |
| `/t [tag]` | by translate-side tag |
| `/d <id>` | delete (super-user only) |
| `/start` | greeting |

## Project layout

```
api/          FastAPI app + static SPA (index.html)
bot/          Telethon bot (`bot/data/` = session)
listener/     OCR worker
core/         shared frapper_core package
data/         SQLite database (bind-mounted directory; contents gitignored)
```

App logs go to container stdout (`docker compose logs` / `./scripts/docker-logs.sh`); Docker rotates them (`json-file`, 10m × 3).
Agent-oriented architecture notes live in [`CLAUDE.md`](CLAUDE.md). Release history: [`CHANGELOG.md`](CHANGELOG.md).

## Notes

- Tests: `./scripts/run-tests.sh`. No CI.
- On a server, keep `FRAPPER_ENABLE_DOCS=false` and proxy only `127.0.0.1:<FRAPPER_API_PORT>` from host Nginx. Do not publish `api` or `redis` to `0.0.0.0`.
- OCR geometry is calibrated to Reverso screenshots (`FrapperConfig`); layout changes need re-calibration.
- Failed Redis jobs sit in DB 1 and are not auto-retried.
- Phrase tag search: substring for tags ≥ 4 characters; exact otherwise; trailing `==` forces exact match.
