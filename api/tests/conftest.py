import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from migrate_db import create_empty_db  # noqa: E402

DB_PATH = Path(tempfile.mkdtemp(prefix='frapper-api-tests-')) / 'frapper.db'
create_empty_db(DB_PATH)

# Must be set before any `app` module is imported: config and DB binding happen at import time.
os.environ.update(
    FRAPPER_USERNAME='test-user',
    FRAPPER_PASSWORD='test-password',
    SQLITE_DB_PATH=str(DB_PATH),
    FRAPPER_ENABLE_DOCS='false',
)

TABLES = ('phrase_pl', 'phrase_en', 'phrase_meta', 'text_en', 'sqlite_sequence')


def _insert_phrase(
    table='phrase_en',
    *,
    target,
    target_tag,
    translate='translation',
    translate_tag='translation',
    active=True,
    message_date='2026-10-01 10:00:00',
):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cursor = conn.execute(
            f'INSERT INTO {table} (meta_id, state, active, target, target_tag, translate, translate_tag, '
            'target_mask, translate_mask, message_id, message_date, metadata, created_at) '
            "VALUES (NULL, 'done', ?, ?, ?, ?, ?, ?, ?, 0, ?, '{}', ?)",
            (
                int(active),
                target,
                target_tag,
                translate,
                translate_tag,
                '1' * len(target.split()),
                '1' * len(translate.split()),
                message_date,
                message_date,
            ),
        )
        return cursor.lastrowid


@pytest.fixture(autouse=True)
def clean_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        for table in TABLES:
            conn.execute(f'DELETE FROM {table}')


@pytest.fixture
def insert_phrase():
    return _insert_phrase


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    test_client = TestClient(app, raise_server_exceptions=False)
    test_client.auth = ('test-user', 'test-password')
    return test_client
