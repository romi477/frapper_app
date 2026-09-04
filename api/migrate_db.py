#!/usr/bin/env python3
"""Migrate SQLite schema for multi-language phrase tables and new phrase_meta shape."""

import sqlite3
import sys
from pathlib import Path


CREATE_EMPTY_SCHEMA = """
CREATE TABLE phrase_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lang TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    datetime_created DATETIME NOT NULL,
    with_error BOOLEAN NOT NULL,
    created_at DATETIME NOT NULL,
    CONSTRAINT unq_phrase_meta__lang_message_id_datetime_created
        UNIQUE (lang, message_id, datetime_created)
);

CREATE TABLE phrase_pl (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_id INTEGER REFERENCES phrase_meta (id) ON DELETE CASCADE,
    state TEXT NOT NULL,
    active BOOLEAN NOT NULL,
    target TEXT NOT NULL,
    target_tag TEXT NOT NULL,
    translate TEXT NOT NULL,
    translate_tag TEXT NOT NULL,
    target_mask TEXT NOT NULL,
    translate_mask TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    message_date DATETIME NOT NULL,
    metadata TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    CONSTRAINT unq_phrase_pl__target_target_tag UNIQUE (target, target_tag)
);
CREATE INDEX idx_phrase_pl__meta_id ON phrase_pl (meta_id);

CREATE TABLE phrase_en (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_id INTEGER REFERENCES phrase_meta (id) ON DELETE CASCADE,
    state TEXT NOT NULL,
    active BOOLEAN NOT NULL,
    target TEXT NOT NULL,
    target_tag TEXT NOT NULL,
    translate TEXT NOT NULL,
    translate_tag TEXT NOT NULL,
    target_mask TEXT NOT NULL,
    translate_mask TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    message_date DATETIME NOT NULL,
    metadata TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    CONSTRAINT unq_phrase_en__target_target_tag UNIQUE (target, target_tag)
);
CREATE INDEX idx_phrase_en__meta_id ON phrase_en (meta_id);

CREATE TABLE text_en (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
"""


def table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def column_exists(conn, table, column):
    rows = conn.execute(f'PRAGMA table_info({table})').fetchall()
    return any(row[1] == column for row in rows)


def migrate_phrase_meta(conn):
    if column_exists(conn, 'phrase_meta', 'datetime_created'):
        print('phrase_meta: already migrated')
        return

    conn.executescript(
        """
        CREATE TABLE phrase_meta_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lang TEXT NOT NULL,
            state TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            datetime_created DATETIME NOT NULL,
            with_error BOOLEAN NOT NULL,
            created_at DATETIME NOT NULL,
            CONSTRAINT unq_phrase_meta__lang_message_id_datetime_created
                UNIQUE (lang, message_id, datetime_created)
        );

        INSERT INTO phrase_meta_new (
            id, lang, state, message_id, datetime_created, with_error, created_at
        )
        SELECT
            id,
            'pl',
            state,
            message_id,
            message_date,
            with_error,
            created_at
        FROM phrase_meta;

        DROP TABLE phrase_meta;
        ALTER TABLE phrase_meta_new RENAME TO phrase_meta;
        """
    )
    print('phrase_meta: migrated (removed channel_id, added lang, renamed message_date -> datetime_created)')


def make_meta_id_nullable(conn, table):
    if not table_exists(conn, table):
        return
    rows = conn.execute(f'PRAGMA table_info({table})').fetchall()
    meta_col = next((row for row in rows if row[1] == 'meta_id'), None)
    if not meta_col or meta_col[3] == 0:
        print(f'{table}: meta_id already nullable')
        return

    unq = f'unq_{table}__target_target_tag'
    conn.executescript(
        f"""
        CREATE TABLE {table}_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_id INTEGER REFERENCES phrase_meta (id) ON DELETE CASCADE,
            state TEXT NOT NULL,
            active BOOLEAN NOT NULL,
            target TEXT NOT NULL,
            target_tag TEXT NOT NULL,
            translate TEXT NOT NULL,
            translate_tag TEXT NOT NULL,
            target_mask TEXT NOT NULL,
            translate_mask TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            message_date DATETIME NOT NULL,
            metadata TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            CONSTRAINT {unq} UNIQUE (target, target_tag)
        );
        INSERT INTO {table}_new SELECT * FROM {table};
        DROP TABLE {table};
        ALTER TABLE {table}_new RENAME TO {table};
        CREATE INDEX idx_{table}__meta_id ON {table} (meta_id);
        """
    )
    print(f'{table}: meta_id is now nullable')


def drop_phrase_meta_state(conn):
    if not table_exists(conn, 'phrase_meta'):
        return
    if not column_exists(conn, 'phrase_meta', 'state'):
        print('phrase_meta: state column already absent')
        return
    conn.execute('ALTER TABLE phrase_meta DROP COLUMN state')
    print('phrase_meta: dropped state column')


def migrate_phrase_pl(conn):
    drop_phrase_lang_column(conn, 'phrase_pl')
    make_meta_id_nullable(conn, 'phrase_pl')


def drop_phrase_lang_column(conn, table):
    if not table_exists(conn, table):
        return
    if not column_exists(conn, table, 'lang'):
        print(f'{table}: lang column already absent')
        return
    conn.execute(f'ALTER TABLE {table} DROP COLUMN lang')
    print(f'{table}: dropped lang column')


def migrate_phrase_en(conn):
    if table_exists(conn, 'phrase_en'):
        drop_phrase_lang_column(conn, 'phrase_en')
        make_meta_id_nullable(conn, 'phrase_en')
        return

    conn.executescript(
        """
        CREATE TABLE phrase_en (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_id INTEGER REFERENCES phrase_meta (id) ON DELETE CASCADE,
            state TEXT NOT NULL,
            active BOOLEAN NOT NULL,
            target TEXT NOT NULL,
            target_tag TEXT NOT NULL,
            translate TEXT NOT NULL,
            translate_tag TEXT NOT NULL,
            target_mask TEXT NOT NULL,
            translate_mask TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            message_date DATETIME NOT NULL,
            metadata TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            CONSTRAINT unq_phrase_en__target_target_tag UNIQUE (target, target_tag)
        );
        CREATE INDEX idx_phrase_en__meta_id ON phrase_en (meta_id);
        """
    )
    print('phrase_en: created')


def migrate_text_en(conn):
    if table_exists(conn, 'text_en'):
        print('text_en: already exists')
        return

    conn.executescript(
        """
        CREATE TABLE text_en (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
        """
    )
    print('text_en: created')


def migrate(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('PRAGMA foreign_keys=OFF')
        migrate_phrase_meta(conn)
        migrate_phrase_pl(conn)
        migrate_phrase_en(conn)
        migrate_text_en(conn)
        drop_phrase_meta_state(conn)
        conn.commit()
    finally:
        conn.close()


def db_needs_init(db_path: Path) -> bool:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return True

    conn = sqlite3.connect(db_path)
    try:
        return not table_exists(conn, 'phrase_meta')
    finally:
        conn.close()


def create_empty_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(CREATE_EMPTY_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def ensure_db(db_path: Path) -> str:
    db_path = db_path.resolve()
    if db_needs_init(db_path):
        create_empty_db(db_path)
        print(f'Created empty database: {db_path}')
        return 'created'

    migrate(db_path)
    return 'existing'


if __name__ == '__main__':
    args = sys.argv[1:]
    init_mode = '--init' in args
    if init_mode:
        args.remove('--init')

    path = Path(args[0] if args else 'frapper.db').resolve()
    if init_mode:
        status = ensure_db(path)
        print(f'Database ready ({status}): {path}')
    else:
        migrate(path)
        print(f'Migration complete: {path}')
