from datetime import datetime

from pony.orm import Optional, PrimaryKey, Required

from . import db


class TextEn(db.Entity):

    _table_ = 'text_en'

    id = PrimaryKey(int, auto=True)
    title = Required(str)
    body = Required(str)
    tags = Optional(str, default='')
    created_at = Required(datetime, default=lambda: datetime.now())
    updated_at = Required(datetime, default=lambda: datetime.now())
