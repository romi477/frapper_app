FROM python:3.11-slim-bookworm AS base

ENV APP_PATH=/opt/api

WORKDIR $APP_PATH


FROM base AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_DEV=1

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /bin/uv

WORKDIR /opt/src
COPY pyproject.toml uv.lock ./
COPY core ./core
COPY api/pyproject.toml ./api/
COPY bot/pyproject.toml ./bot/
COPY listener/pyproject.toml ./listener/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package frapper-api --no-install-project --no-editable


FROM base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=$APP_PATH \
    VIRTUAL_ENV=/opt/src/.venv \
    PATH=/opt/src/.venv/bin:$PATH

COPY --from=builder /opt/src/.venv /opt/src/.venv
COPY api/migrate_db.py /opt/api/migrate_db.py
COPY api/app /opt/api/app

CMD ["python", "-m", "app"]
