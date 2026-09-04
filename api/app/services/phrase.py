from datetime import date, datetime
from typing import List, Optional

from pony.orm import count, db_session, select

from app.lang import get_phrase_entity, validate_lang
from app.schemas.phrase_schema import PhraseSchema


def _tag_from_text_mask(text: str, mask: str) -> str:
    words = text.split()
    return ' '.join(word for word, flag in zip(words, mask) if flag == '1')


def _required_tag(text: str, mask: str) -> str:
    tag = _tag_from_text_mask(text, mask)
    return tag if tag else '-'


def _tag_condition(tag: str) -> str:
    # Must match lower(target_tag) / lower(translate_tag) in callers.
    tag = tag.lower()
    if tag.endswith('=='):
        return f"= '{tag[:-2]}'"
    if len(tag) >= 4:
        return f"LIKE '%{tag}%'"
    return f"= '{tag}'"


@db_session
def post_phrases(model_list: List[PhraseSchema], lang: str):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    records = [entity(**x.model_dump()) for x in model_list]
    return [x.to_dict() for x in records]


@db_session
def create_phrase(
    lang: str,
    target: str,
    translate: str,
    target_mask: str,
    translate_mask: str,
) -> dict:
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    target = target.strip()
    translate = translate.strip()
    now = datetime.now()
    record = entity(
        meta_id=None,
        state='done',
        active=True,
        target=target,
        target_tag=_required_tag(target, target_mask),
        translate=translate,
        translate_tag=_required_tag(translate, translate_mask),
        target_mask=target_mask,
        translate_mask=translate_mask,
        message_id=0,
        message_date=now,
        created_at=now,
        metadata='{}',
    )
    return record.to_dict()


@db_session
def read_target_tag(lang: str, tag: str = None):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    table = entity._table_

    if tag:
        condition = _tag_condition(tag)
        query = f"""
            SELECT * FROM {table}
            WHERE active = true AND lower(target_tag) {condition}
            """
    else:
        # lower() on both sides — raw subquery tag breaks on mixed case → [].
        query = f"""
            SELECT * FROM {table}
            WHERE active = true AND lower(target_tag) = (
                SELECT lower(target_tag) FROM {table}
                WHERE active = true
                ORDER BY RANDOM() LIMIT 1
            )
        """

    records = entity.select_by_sql(query)
    return [x.to_dict() for x in records]


@db_session
def read_translate_tag(lang: str, tag: str = None):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    table = entity._table_

    if tag:
        condition = _tag_condition(tag)
        query = f"""
            SELECT * FROM {table}
            WHERE active = true AND lower(translate_tag) {condition}
            """
    else:
        query = f"""
            SELECT * FROM {table}
            WHERE active = true AND lower(translate_tag) = (
                SELECT lower(translate_tag) FROM {table}
                WHERE active = true
                ORDER BY RANDOM() LIMIT 1
            )
        """

    records = entity.select_by_sql(query)
    return [x.to_dict() for x in records]


@db_session
def read_phrase_stats():
    stats = {}
    for lang in ('pl', 'en'):
        entity = get_phrase_entity(lang)
        stats[lang] = {
            'count': count(r for r in entity if r.active),
            'max_id': select(max(r.id) for r in entity if r.active).first() or 0,
        }
    return stats


@db_session
def read_target_count(lang: str, count: int = 10):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    table = entity._table_
    records = entity.select_by_sql(
        f"""
        SELECT * FROM {table}
        WHERE active = true
        ORDER BY RANDOM() LIMIT {count}
        """
    )
    return [x.to_dict() for x in records]


@db_session
def read_target_slice(lang: str, since_id: int, count: int = 10):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    table = entity._table_
    records = entity.select_by_sql(
        f"""
        SELECT * FROM {table}
        WHERE id >= {since_id} AND active = true
        LIMIT {count}
        """
    )
    return [x.to_dict() for x in records]


@db_session
def read_phrases_by_date(lang: str, on_date: date):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    table = entity._table_
    date_str = on_date.isoformat()
    records = entity.select_by_sql(
        f"""
        SELECT * FROM {table}
        WHERE active = true AND date(message_date) = '{date_str}'
        ORDER BY id
        """
    )
    return [x.to_dict() for x in records]


@db_session
def count_phrases_by_date(lang: str, on_date: date) -> int:
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    return count(
        r for r in entity if r.active and r.message_date.date() == on_date
    )


@db_session
def read_target_from_tail(lang: str, tail: int = 100, count: int = 10):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    table = entity._table_
    records = entity.select_by_sql(
        f"""
        SELECT *
        FROM {table}
        WHERE id > (SELECT COUNT(*) - {tail} FROM {table})
        ORDER BY RANDOM()
        LIMIT {count}
        """
    )
    return [x.to_dict() for x in records]


@db_session
def read_phrase_by_id(lang: str, item_id: int):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    record = entity.get(id=item_id)
    if not record:
        return []
    return [record.to_dict()]


@db_session
def update_phrase(
    lang: str,
    item_id: int,
    target: str,
    translate: str,
    target_mask: str,
    translate_mask: str,
) -> Optional[dict]:
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    record = entity.get(id=item_id)
    if not record:
        return None

    target = target.strip()
    translate = translate.strip()

    record.target = target
    record.translate = translate
    record.target_mask = target_mask
    record.translate_mask = translate_mask
    record.target_tag = _required_tag(target, target_mask)
    record.translate_tag = _required_tag(translate, translate_mask)
    return record.to_dict()


@db_session
def delete_phrase(lang: str, item_id: int):
    validate_lang(lang)
    entity = get_phrase_entity(lang)
    record = entity.get(id=item_id)
    if not record:
        return {'message': 'Record not found'}

    record.delete()
    return {'message': 'Record deleted successfully'}
