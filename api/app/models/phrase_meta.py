from datetime import datetime

from pony.orm import PrimaryKey, Required, Set, composite_key

from . import db


class PhraseMeta(db.Entity):

    _table_ = 'phrase_meta'

    id = PrimaryKey(int, auto=True)
    lang = Required(str)
    message_id = Required(int)
    datetime_created = Required(datetime)
    with_error = Required(bool)
    created_at = Required(datetime, default=lambda: datetime.now())

    composite_key(lang, message_id, datetime_created)

    phrase_pl = Set('PhrasePl')
    phrase_en = Set('PhraseEn')
