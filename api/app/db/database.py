from pathlib import Path

from pony.orm import Database

from app.config import config

API_ROOT = Path(__file__).resolve().parents[2]


def sqlite_filename(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str(API_ROOT / candidate)


db = Database()
db.bind(provider='sqlite', filename=sqlite_filename(config.sqlite_db_path), create_db=False)
