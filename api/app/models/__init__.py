from ..db.database import db

from . import phrase_en
from . import phrase_meta
from . import phrase_pl
from . import text_en


db.generate_mapping(create_tables=False)
