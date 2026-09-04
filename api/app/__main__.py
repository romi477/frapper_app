import logging
import sys
from pathlib import Path

import uvicorn

from migrate_db import ensure_db

from app.config import config
from app.db.database import sqlite_filename


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
_logger = logging.getLogger('frapper-api')

db_path = Path(sqlite_filename(config.sqlite_db_path))
status = ensure_db(db_path)
_logger.info('Database ready (%s): %s', status, db_path)

uvicorn.run(
    'app.main:app',
    host='0.0.0.0',
    port=config.frapper_api_port,
    reload=False,
)
