import re
from datetime import datetime
from typing import List, Optional

from pony.orm import db_session

from app.models.text_en import TextEn
from app.services.text_body import prepare_text_body

_TRAILING_TAG_PUNCT = re.compile(r'[.,?]+$')


def _clean_tag(part: str) -> str:
    text = ' '.join(str(part or '').split()).lower()
    return _TRAILING_TAG_PUNCT.sub('', text).strip()


def _split_tags(tags: str) -> List[str]:
    normalized = str(tags or '').replace(',', ';')
    seen = set()
    parts = []
    for part in normalized.split(';'):
        text = _clean_tag(part)
        if not text or text in seen:
            continue
        seen.add(text)
        parts.append(text)
    return parts


def _normalize_tags(raw: str) -> str:
    return ';'.join(_split_tags(raw))


@db_session
def create_text(title: str, body: str, tags: str = '') -> dict:
    now = datetime.now()
    record = TextEn(
        title=title.strip(),
        body=prepare_text_body(body),
        tags=_normalize_tags(tags),
        created_at=now,
        updated_at=now,
    )
    return record.to_dict()


def _tags_match(tags: str, tag: str) -> bool:
    query = tag.strip().lower()
    if not query:
        return True
    parts = [part.lower() for part in _split_tags(tags)]
    if query.endswith('=='):
        exact = query[:-2]
        return exact in parts
    if len(query) >= 4:
        return any(query in part for part in parts) or query in tags.lower()
    return query in parts


@db_session
def read_text_summaries(tag: Optional[str] = None) -> List[dict]:
    records = TextEn.select().order_by(TextEn.id.desc())[:]
    if tag:
        records = [record for record in records if _tags_match(record.tags, tag)]
    return [
        {
            'id': record.id,
            'title': record.title,
            'tags': record.tags,
            'created_at': record.created_at,
        }
        for record in records
    ]


@db_session
def read_text_by_id(item_id: int) -> Optional[dict]:
    record = TextEn.get(id=item_id)
    if not record:
        return None
    return record.to_dict()


@db_session
def update_text(
    item_id: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    tags: Optional[str] = None,
) -> Optional[dict]:
    record = TextEn.get(id=item_id)
    if not record:
        return None

    if title is not None:
        record.title = title.strip()
    if body is not None:
        record.body = prepare_text_body(body)
    if tags is not None:
        record.tags = _normalize_tags(tags)
    record.updated_at = datetime.now()
    return record.to_dict()


@db_session
def delete_text(item_id: int) -> bool:
    record = TextEn.get(id=item_id)
    if not record:
        return False
    record.delete()
    return True
