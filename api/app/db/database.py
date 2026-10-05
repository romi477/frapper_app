from pony.orm import Database

from app.config import config, sqlite_filename


db = Database()
db.bind(provider='sqlite', filename=sqlite_filename(config.sqlite_db_path), create_db=False)
