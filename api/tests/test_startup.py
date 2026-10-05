import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from contextlib import closing
from pathlib import Path

import pytest

from migrate_db import create_empty_db

API_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_TABLES = {'phrase_meta', 'phrase_pl', 'phrase_en', 'text_en'}


def _free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _tables(db_path):
    with closing(sqlite3.connect(db_path)) as conn:
        return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


@pytest.fixture
def run_api(tmp_path):
    started = []

    def run(db_path, timeout=20):
        port = _free_port()
        log_path = tmp_path / f'api-{port}.log'
        env = dict(os.environ, SQLITE_DB_PATH=str(db_path), FRAPPER_API_PORT=str(port))
        with open(log_path, 'w') as log_file:
            proc = subprocess.Popen(
                [sys.executable, '-m', 'app'],
                cwd=API_ROOT,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        started.append(proc)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=1) as response:
                    if response.status == 200:
                        return True, log_path.read_text()
            except OSError:
                time.sleep(0.2)
        return False, log_path.read_text()

    yield run

    for proc in started:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_api_starts_when_db_file_is_missing(tmp_path, run_api):
    db_path = tmp_path / 'frapper.db'

    healthy, log = run_api(db_path)

    assert healthy, log
    assert SCHEMA_TABLES <= _tables(db_path)


def test_api_starts_when_db_file_is_empty(tmp_path, run_api):
    db_path = tmp_path / 'frapper.db'
    db_path.touch()

    healthy, log = run_api(db_path)

    assert healthy, log
    assert SCHEMA_TABLES <= _tables(db_path)


def test_api_migrates_db_missing_text_en_table(tmp_path, run_api):
    db_path = tmp_path / 'frapper.db'
    create_empty_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute('DROP TABLE text_en')

    healthy, log = run_api(db_path)

    assert healthy, log
    assert 'text_en' in _tables(db_path)
