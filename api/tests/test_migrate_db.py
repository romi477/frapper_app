import sqlite3
from contextlib import closing

import pytest

from migrate_db import create_empty_db, ensure_db, migrate


def test_migrate_restores_truncated_window_closing_tag(tmp_path):
    db_path = tmp_path / 'frapper.db'
    create_empty_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute(
            'INSERT INTO text_en (title, body, tags, created_at, updated_at) '
            "VALUES ('story', ?, '', '2026-01-01 00:00:00', '2026-01-01 00:00:00')",
            ('<div class="window">Hi</div',),
        )

    migrate(db_path)

    with closing(sqlite3.connect(db_path)) as conn:
        assert conn.execute('SELECT body FROM text_en').fetchone()[0] == '<div class="window">Hi</div>'


def test_ensure_db_rejects_directory_path(tmp_path):
    with pytest.raises(IsADirectoryError):
        ensure_db(tmp_path)
