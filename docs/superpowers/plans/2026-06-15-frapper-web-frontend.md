# Frapper Web Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a static web frontend (served by the `api` service) that queries phrases via three `/api/phrase-pl` endpoints with highlighted rendering and an accumulating session history, and migrate API auth from Bearer token to HTTP Basic across `api`, `bot`, and `listener`.

**Architecture:** A single self-contained `api/app/static/index.html` (inline CSS + vanilla JS, no build step) is served by FastAPI at `GET /` behind HTTP Basic Auth. The page calls the existing `/api/phrase-pl/*` endpoints with `fetch()`; the browser auto-attaches the cached Basic credentials to same-origin requests. All UI state (mode, history) is client-side.

**Tech Stack:** FastAPI + Pony ORM (existing `api`), Telethon (`bot`), plain `requests` (`bot`/`listener`), vanilla HTML/CSS/JS, Docker Compose.

> **Testing note:** This repository has no test framework, linter config, or CI (see `CLAUDE.md`). Per project convention, verification is **manual** (curl + browser). Do not add pytest or claim automated coverage.

> **Git note:** The repo's `.gitignore` ignores `*.md`, so this plan and the spec are not tracked unless force-added. All code files in the tasks below are normal tracked files — commit them as usual.

---

## File Structure

- **Create:** `api/app/static/index.html` — the entire frontend (markup, styles, script).
- **Modify:** `api/app/utils.py` — replace Bearer dependency with Basic Auth dependency.
- **Modify:** `api/app/config.py` — drop `frapper_api_bearer_token`.
- **Modify:** `api/app/api/phrase_pl.py` — swap auth dependency import/usage.
- **Modify:** `api/app/api/phrase_meta.py` — swap auth dependency import/usage.
- **Modify:** `api/app/main.py` — add the authenticated `GET /` route serving `index.html`.
- **Modify:** `bot/app/config.py` — add `api_docs_username`/`api_docs_password`, drop bearer.
- **Modify:** `bot/app/bot.py` — send Basic Auth on every API call.
- **Modify:** `listener/app/listener.py` — send Basic Auth on the POST.
- **Modify:** `docker-compose.yml` — wire Basic Auth env vars to `bot`/`listener`, drop bearer everywhere.
- **Modify:** `.env.example` — drop `FRAPPER_API_BEARER_TOKEN`.

---

## Task 1: API Basic Auth dependency

**Files:**
- Modify: `api/app/utils.py`
- Modify: `api/app/config.py`

- [ ] **Step 1: Replace `validate_bearer` with `validate_basic` in `api/app/utils.py`**

Replace the entire file contents with:

```python
# python3

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import config


_get_basic_credentials = HTTPBasic()


def validate_basic(credentials: HTTPBasicCredentials = Depends(_get_basic_credentials)) -> str:
    correct_username = secrets.compare_digest(
        credentials.username.encode('utf8'),
        config.api_docs_username.encode('utf8'),
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode('utf8'),
        config.api_docs_password.encode('utf8'),
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials',
            headers={'WWW-Authenticate': 'Basic'},
        )

    return credentials.username
```

- [ ] **Step 2: Drop the bearer token from `api/app/config.py`**

Replace the entire file contents with:

```python
from pydantic_settings import BaseSettings


class Config(BaseSettings):

    api_docs_username: str
    api_docs_password: str

    sqlite_db_path: str


config = Config()
```

- [ ] **Step 3: Verify the module imports**

Run: `cd api && python -c "from app.utils import validate_basic; print('ok')"`
Expected: prints `ok` (requires `API_DOCS_USERNAME`, `API_DOCS_PASSWORD`, `SQLITE_DB_PATH` to be set in the environment; if running outside the container, export dummy values first).

- [ ] **Step 4: Commit**

```bash
git add api/app/utils.py api/app/config.py
git commit -m "feat(api): replace bearer dependency with HTTP Basic auth"
```

---

## Task 2: Swap auth dependency in routers

**Files:**
- Modify: `api/app/api/phrase_pl.py`
- Modify: `api/app/api/phrase_meta.py`

- [ ] **Step 1: Update the import in `api/app/api/phrase_pl.py`**

Replace line:

```python
from ..utils import validate_bearer
```

with:

```python
from ..utils import validate_basic
```

- [ ] **Step 2: Swap every dependency usage in `api/app/api/phrase_pl.py`**

Replace all occurrences of `Depends(validate_bearer)` with `Depends(validate_basic)`. There are 7 occurrences (the `post`, `target-tag`, `translate-tag`, `fetch-count`, `fetch-slice`, `fetch-tail`, and `delete` routes).

- [ ] **Step 3: Update `api/app/api/phrase_meta.py`**

Replace line:

```python
from ..utils import validate_bearer
```

with:

```python
from ..utils import validate_basic
```

and replace `Depends(validate_bearer)` with `Depends(validate_basic)` on the POST route.

- [ ] **Step 4: Verify no stale references remain**

Run: `rg "validate_bearer" api/`
Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add api/app/api/phrase_pl.py api/app/api/phrase_meta.py
git commit -m "feat(api): use Basic auth dependency on phrase routers"
```

---

## Task 3: Serve the frontend page route

**Files:**
- Modify: `api/app/main.py`

- [ ] **Step 1: Replace `api/app/main.py` with the authenticated page route**

Replace the entire file contents with:

```python
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse

from app.api import router
from app.utils import validate_basic


STATIC_DIR = Path(__file__).parent / 'static'

app = FastAPI(
    title='Frapper API',
    description='Frapper API',
    version='1.0.0',
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(router)


@app.get('/', dependencies=[Depends(validate_basic)], include_in_schema=False)
def serve_index():
    return FileResponse(STATIC_DIR / 'index.html')
```

- [ ] **Step 2: Create the static directory placeholder check**

Run: `mkdir -p api/app/static`
Expected: directory exists (the file is created in Task 4).

- [ ] **Step 3: Commit**

```bash
git add api/app/main.py
git commit -m "feat(api): serve frontend index.html at / behind Basic auth"
```

---

## Task 4: Build the frontend page

**Files:**
- Create: `api/app/static/index.html`

- [ ] **Step 1: Create `api/app/static/index.html` with the full page**

Create the file with exactly this content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Frapper</title>
<style>
  :root {
    --bg: #f5f6f8;
    --card: #ffffff;
    --border: #e7e9ee;
    --text: #232834;
    --muted: #7b8494;
    --accent: #f0b429;
    --highlight: rgba(240, 180, 41, 0.32);
    --amber-soft: #fdf1cf;
    --amber-border: #f0d28a;
    --amber-text: #8a6400;
    --chip-bg: #eef1f5;
    --chip-text: #5b6472;
    --error: #b4232a;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.5;
  }
  header.bar {
    position: sticky; top: 0;
    background: rgba(245,246,248,0.9);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--border);
    padding: 16px 0;
    z-index: 10;
  }
  .wrap { max-width: 680px; margin: 0 auto; padding: 0 20px; }
  .brand { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; }
  .brand h1 { font-size: 18px; margin: 0; letter-spacing: .5px; }
  .brand span { color: var(--muted); font-size: 13px; }

  .modes { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
  .pill {
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--muted);
    padding: 7px 16px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all .15s ease;
  }
  .pill:hover { border-color: var(--amber-border); }
  .pill.active {
    background: var(--amber-soft);
    color: var(--amber-text);
    border-color: var(--amber-border);
  }

  .input-row { display: flex; align-items: center; gap: 10px; }
  .input-row input {
    flex: 1;
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 12px 15px;
    border-radius: 12px;
    font-size: 15px;
    outline: none;
  }
  .input-row input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(240,180,41,0.18); }
  .input-row input::placeholder { color: #a3aab6; }
  .hint { color: var(--muted); font-size: 12px; white-space: nowrap; }

  .clear-fab {
    position: fixed;
    top: 22px; right: 26px;
    z-index: 20;
    display: inline-flex; align-items: center; gap: 7px;
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 9px 15px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(20,28,48,0.06);
  }
  .clear-fab:hover { color: var(--error); border-color: #efc2c4; background: #fff5f5; }
  .clear-fab svg { width: 14px; height: 14px; }

  main { padding: 24px 0 60px; }

  .batch-label {
    display: flex; align-items: center; gap: 10px;
    color: var(--muted); font-size: 12px;
    margin: 6px 0 12px;
  }
  .batch-label::before, .batch-label::after {
    content: ""; flex: 1; height: 1px; background: var(--border);
  }
  .batch-label.error { color: var(--error); }

  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 1px 2px rgba(20,28,48,0.04), 0 4px 14px rgba(20,28,48,0.03);
  }
  .id-chip {
    display: inline-flex; align-items: baseline; gap: 2px;
    background: var(--chip-bg);
    color: var(--chip-text);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: .3px;
    padding: 3px 11px;
    border-radius: 999px;
    margin-bottom: 12px;
  }
  .id-chip .hash { color: var(--accent); font-weight: 700; }
  .target { font-size: 18px; margin: 0 0 10px; }
  .translate { font-size: 16px; color: var(--muted); font-style: italic; margin: 0; }
  mark {
    background: var(--highlight);
    color: inherit;
    padding: 0 3px;
    border-radius: 3px;
  }

  .loader-box { display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 50px 0; }
  .spinner {
    width: 30px; height: 30px;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loader-box p { color: var(--muted); font-size: 13px; margin: 0; }
</style>
</head>
<body>
  <button class="clear-fab" id="clear-btn" title="Clear all results">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>
    Clear
  </button>

  <header class="bar">
    <div class="wrap">
      <div class="brand"><h1>FRAPPER</h1><span>Polish phrase trainer</span></div>
      <div class="modes" id="modes">
        <div class="pill active" data-mode="count">Count</div>
        <div class="pill" data-mode="tail">Tail</div>
        <div class="pill" data-mode="tag">Tag</div>
      </div>
      <div class="input-row">
        <input id="query" autocomplete="off" autofocus>
        <span class="hint">↵ Enter</span>
      </div>
    </div>
  </header>

  <main>
    <div class="wrap">
      <div id="loader" class="loader-box" style="display:none">
        <div class="spinner"></div>
        <p>Loading phrases…</p>
      </div>
      <div id="results"></div>
    </div>
  </main>

<script>
  const API = '/api/phrase-pl';
  const MIN_LOADER_MS = 1000;
  const TAIL_COUNT = 10;

  const MODES = {
    count: {
      label: 'Count',
      placeholder: 'How many random phrases?  (press Enter)',
      build(value) {
        const url = new URL(API + '/fetch-count', location.origin);
        if (value) url.searchParams.set('count', value);
        return { url, desc: value || 'default' };
      },
    },
    tail: {
      label: 'Tail',
      placeholder: 'Tail window (most recent N rows)  (press Enter)',
      build(value) {
        const url = new URL(API + '/fetch-tail', location.origin);
        if (value) {
          url.searchParams.set('tail', value);
          url.searchParams.set('count', TAIL_COUNT);
        }
        return { url, desc: value ? value + ' / ' + TAIL_COUNT : 'default' };
      },
    },
    tag: {
      label: 'Tag',
      placeholder: 'Polish construction tag, or empty for a random one  (press Enter)',
      build(value) {
        const url = new URL(API + '/target-tag', location.origin);
        if (value) url.searchParams.set('tag', value);
        return { url, desc: value ? '"' + value + '"' : 'random' };
      },
    },
  };

  let currentMode = 'count';

  const modesEl = document.getElementById('modes');
  const queryEl = document.getElementById('query');
  const loaderEl = document.getElementById('loader');
  const resultsEl = document.getElementById('results');
  const clearBtn = document.getElementById('clear-btn');

  function setMode(mode) {
    currentMode = mode;
    for (const pill of modesEl.children) {
      pill.classList.toggle('active', pill.dataset.mode === mode);
    }
    queryEl.placeholder = MODES[mode].placeholder;
    queryEl.value = '';
    queryEl.focus();
  }

  modesEl.addEventListener('click', (e) => {
    const pill = e.target.closest('.pill');
    if (pill) setMode(pill.dataset.mode);
  });

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function rebuildString(sentence, mask) {
    const words = sentence.split(' ');
    const out = [];
    for (let i = 0; i < words.length; i++) {
      const word = escapeHtml(words[i]);
      if (mask[i] === '1') {
        out.push('<mark>' + word + '</mark>');
      } else {
        out.push(word);
      }
    }
    return out.join(' ');
  }

  function makeCard(item) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML =
      '<div class="id-chip"><span class="hash">#</span>' + escapeHtml(String(item.id)) + '</div>' +
      '<p class="target">' + rebuildString(item.target, item.target_mask) + '</p>' +
      '<p class="translate">' + rebuildString(item.translate, item.translate_mask) + '</p>';
    return card;
  }

  function prependBatch(labelText, nodes, isError) {
    const label = document.createElement('div');
    label.className = 'batch-label' + (isError ? ' error' : '');
    label.textContent = labelText;

    const frag = document.createDocumentFragment();
    frag.appendChild(label);
    for (const node of nodes) frag.appendChild(node);

    resultsEl.insertBefore(frag, resultsEl.firstChild);
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function runQuery() {
    const value = queryEl.value.trim();
    const mode = MODES[currentMode];
    const { url, desc } = mode.build(value);

    loaderEl.style.display = 'flex';

    try {
      const [response] = await Promise.all([fetch(url), sleep(MIN_LOADER_MS)]);

      if (!response.ok) {
        prependBatch(mode.label + ' · ' + desc + ' · error ' + response.status, [], true);
        return;
      }

      const data = await response.json();

      if (!Array.isArray(data) || data.length === 0) {
        prependBatch(mode.label + ' · ' + desc + ' · not found', [], false);
        return;
      }

      const cards = data.map(makeCard);
      prependBatch(mode.label + ' · ' + desc + ' · ' + data.length + ' result(s)', cards, false);
    } catch (err) {
      prependBatch(mode.label + ' · ' + desc + ' · network error', [], true);
    } finally {
      loaderEl.style.display = 'none';
      queryEl.focus();
    }
  }

  queryEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      runQuery();
    }
  });

  clearBtn.addEventListener('click', () => {
    resultsEl.innerHTML = '';
    queryEl.focus();
  });

  setMode('count');
</script>
</body>
</html>
```

- [ ] **Step 2: Verify the file is valid HTML (no syntax check tooling required)**

Run: `rg -n "runQuery|rebuildString|setMode" api/app/static/index.html`
Expected: matches for all three function names (confirms the script block was written).

- [ ] **Step 3: Commit**

```bash
git add api/app/static/index.html
git commit -m "feat(api): add Frapper frontend page (Count/Tail/Tag, history, loader)"
```

---

## Task 5: Migrate the bot to Basic Auth

**Files:**
- Modify: `bot/app/config.py`
- Modify: `bot/app/bot.py`

- [ ] **Step 1: Update `bot/app/config.py`**

Replace the entire file contents with:

```python
from pydantic_settings import BaseSettings


class Config(BaseSettings):

    redis_host: str
    redis_port: int

    frapper_api_host: str
    frapper_bot_token: str

    api_docs_username: str
    api_docs_password: str

    tg_frapper_id: int
    tg_phrase_pl_id: int
    tg_api_id: int
    tg_su_id: int
    tg_api_hash: str


config = Config()
```

- [ ] **Step 2: Replace the auth header with a Basic auth tuple in `bot/app/bot.py`**

Replace this block:

```python
HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'FrapperBot/0.1.0',
    'Authorization': f'Bearer {config.frapper_api_bearer_token}'
}
```

with:

```python
HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'FrapperBot/0.1.0',
}

AUTH = (config.api_docs_username, config.api_docs_password)
```

- [ ] **Step 3: Pass `auth=AUTH` on the meta POST in `bot/app/bot.py`**

Replace:

```python
    response = requests.post(ENDPOINT_META, json=data, headers=HEADERS)
```

with:

```python
    response = requests.post(ENDPOINT_META, json=data, headers=HEADERS, auth=AUTH)
```

- [ ] **Step 4: Pass `auth=AUTH` on the delete call in `bot/app/bot.py`**

Replace:

```python
    response = requests.delete(f'{ENDPOINT_PHRASE_PL}/{args[0]}', headers=HEADERS)
```

with:

```python
    response = requests.delete(f'{ENDPOINT_PHRASE_PL}/{args[0]}', headers=HEADERS, auth=AUTH)
```

- [ ] **Step 5: Pass `auth=AUTH` in `_perform_request` in `bot/app/bot.py`**

Replace:

```python
    response = requests.get(url, params=params, headers=HEADERS)
```

with:

```python
    response = requests.get(url, params=params, headers=HEADERS, auth=AUTH)
```

- [ ] **Step 6: Verify no stale bearer references remain in the bot**

Run: `rg "bearer|Bearer" bot/`
Expected: no matches.

- [ ] **Step 7: Commit**

```bash
git add bot/app/config.py bot/app/bot.py
git commit -m "feat(bot): authenticate to API with HTTP Basic"
```

---

## Task 6: Migrate the listener to Basic Auth

**Files:**
- Modify: `listener/app/listener.py`

- [ ] **Step 1: Replace the header/auth setup in `listener/app/listener.py`**

Replace this block:

```python
HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'FrapperListener/0.1.0',
    'Authorization': f'Bearer {os.getenv("FRAPPER_API_BEARER_TOKEN")}',
}
ENDPOINT_PHRASE_PL = f'{os.getenv("FRAPPER_API_HOST")}/api/phrase-pl'
```

with:

```python
HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'FrapperListener/0.1.0',
}
AUTH = (os.getenv('API_DOCS_USERNAME'), os.getenv('API_DOCS_PASSWORD'))
ENDPOINT_PHRASE_PL = f'{os.getenv("FRAPPER_API_HOST")}/api/phrase-pl'
```

- [ ] **Step 2: Pass `auth=AUTH` on the POST in `listener/app/listener.py`**

Replace:

```python
        response = requests.post(ENDPOINT_PHRASE_PL, json=data, headers=HEADERS)
```

with:

```python
        response = requests.post(ENDPOINT_PHRASE_PL, json=data, headers=HEADERS, auth=AUTH)
```

- [ ] **Step 3: Verify no stale bearer references remain in the listener**

Run: `rg "bearer|Bearer" listener/`
Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add listener/app/listener.py
git commit -m "feat(listener): authenticate to API with HTTP Basic"
```

---

## Task 7: Update Docker Compose and env example

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`

- [ ] **Step 1: Update the `api` service environment in `docker-compose.yml`**

In the `api` service's `environment:` block, remove the line:

```yaml
      FRAPPER_API_BEARER_TOKEN: ${FRAPPER_API_BEARER_TOKEN}
```

Keep `API_DOCS_USERNAME` and `API_DOCS_PASSWORD`.

- [ ] **Step 2: Update the `bot` service environment in `docker-compose.yml`**

In the `bot` service's `environment:` block, remove:

```yaml
      FRAPPER_API_BEARER_TOKEN: ${FRAPPER_API_BEARER_TOKEN}
```

and add:

```yaml
      API_DOCS_USERNAME: ${API_DOCS_USERNAME}
      API_DOCS_PASSWORD: ${API_DOCS_PASSWORD}
```

- [ ] **Step 3: Update the `listener` service environment in `docker-compose.yml`**

In the `listener` service's `environment:` block, remove:

```yaml
      FRAPPER_API_BEARER_TOKEN: ${FRAPPER_API_BEARER_TOKEN}
```

and add:

```yaml
      API_DOCS_USERNAME: ${API_DOCS_USERNAME}
      API_DOCS_PASSWORD: ${API_DOCS_PASSWORD}
```

- [ ] **Step 4: Update `.env.example`**

Remove the line:

```
FRAPPER_API_BEARER_TOKEN=<..>
```

Keep `API_DOCS_USERNAME` and `API_DOCS_PASSWORD` (they are now the active credentials).

- [ ] **Step 5: Verify no stale bearer references remain anywhere**

Run: `rg "FRAPPER_API_BEARER_TOKEN|frapper_api_bearer_token" .`
Expected: no matches.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore: wire Basic auth env vars, drop bearer token"
```

---

## Task 8: Manual end-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Ensure `.env` has Basic credentials**

Confirm `.env` defines `API_DOCS_USERNAME` and `API_DOCS_PASSWORD` (copy from `.env.example` if needed and fill in values).

- [ ] **Step 2: Build and start the stack**

Run: `docker compose up --build`
Expected: `api`, `redis`, `bot`, `listener` start without auth/config errors.

- [ ] **Step 3: Verify the API rejects unauthenticated requests**

Run: `curl -i http://127.0.0.1:4040/api/phrase-pl/fetch-count`
Expected: `HTTP/1.1 401 Unauthorized` with a `WWW-Authenticate: Basic` header.

- [ ] **Step 4: Verify the API accepts Basic credentials**

Run: `curl -i -u "$API_DOCS_USERNAME:$API_DOCS_PASSWORD" "http://127.0.0.1:4040/api/phrase-pl/fetch-count?count=2"`
Expected: `HTTP/1.1 200 OK` and a JSON array (length up to 2, depending on data).

- [ ] **Step 5: Verify the page is protected and served**

Run: `curl -i http://127.0.0.1:4040/`
Expected: `401 Unauthorized`.
Run: `curl -i -u "$API_DOCS_USERNAME:$API_DOCS_PASSWORD" http://127.0.0.1:4040/`
Expected: `200 OK` and HTML containing `FRAPPER`.

- [ ] **Step 6: Browser check**

Open `http://127.0.0.1:4040/`, authenticate via the browser's Basic dialog, then:
- Count: type `5`, press Enter → up to 5 cards appear under a `Count · 5 · N result(s)` label after a ~1s loader.
- Tail: switch mode, type `100`, press Enter → cards appear (uses `count=10`).
- Tag: switch mode, press Enter with empty input → a random construction's phrases appear; then type a known tag and press Enter.
- Confirm highlighted words match the masks, each new batch is prepended on top, and **Clear** empties the list.

- [ ] **Step 7: Verify bot + listener still reach the API**

Post a screenshot to the phrase channel (or inspect logs): `docker compose logs -f listener` should show successful POSTs (HTTP 200), and `docker compose logs -f bot` should show successful command queries — confirming Basic Auth works service-to-service.

---

## Self-Review (completed by plan author)

- **Spec coverage:** Auth migration (Tasks 1, 2, 5, 6, 7), page route behind Basic (Task 3), frontend with three modes / highlighting / history / Clear / ~1s loader (Task 4), manual verification (Task 8). All spec sections map to tasks.
- **Placeholder scan:** No TBD/TODO; all code blocks are complete and concrete.
- **Type/name consistency:** `validate_basic` defined in Task 1 and referenced in Tasks 2–3; `AUTH` tuple defined and used consistently in bot (Task 5) and listener (Task 6); `API_DOCS_USERNAME`/`API_DOCS_PASSWORD` used consistently across config, compose, and env.
- **Note:** Tag mode intentionally uses `target-tag` only (per spec scope; `translate-tag` and `fetch-slice` are out of scope).
