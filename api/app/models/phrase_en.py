from datetime import datetime

from pony.orm import Optional, PrimaryKey, Required, composite_key

from . import db
from .phrase_meta import PhraseMeta


class PhraseEn(db.Entity):

    _table_ = 'phrase_en'

    id = PrimaryKey(int, auto=True)
    meta_id = Optional(PhraseMeta, reverse='phrase_en')
    state = Required(str)
    active = Required(bool)
    target = Required(str)
    target_tag = Required(str)
    translate = Required(str)
    translate_tag = Required(str)
    target_mask = Required(str)
    translate_mask = Required(str)
    message_id = Required(int)
    message_date = Required(datetime)
    metadata = Required(str)
    created_at = Required(datetime, default=lambda: datetime.now())

    composite_key(target, target_tag)
