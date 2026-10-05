from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pony.orm import db_session

from frapper_core.constants import DATETIME_FORMAT

from app.lang import LangQuery, validate_lang
from app.models.phrase_meta import PhraseMeta
from app.schemas.phrase_meta_schema import PhraseMetaSchema
from app.utils import validate_basic


router = APIRouter(prefix='/phrase-meta', tags=['phrase-meta'])


def _parse_datetime_created(value: str) -> datetime:
    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'datetime_created must match {DATETIME_FORMAT}',
        ) from exc


@router.get('', dependencies=[Depends(validate_basic)])
@db_session
def get_phrase_meta(
    lang: LangQuery,
    message_id: int = Query(...),
    datetime_created: str = Query(...),
):
    lang = validate_lang(lang)
    created = _parse_datetime_created(datetime_created)
    record = PhraseMeta.get(lang=lang, message_id=message_id, datetime_created=created)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Record not found')
    return record.to_dict()


@router.post('', dependencies=[Depends(validate_basic)])
@db_session
def post_phrase_meta(model: PhraseMetaSchema, lang: LangQuery):
    lang = validate_lang(lang)
    created = _parse_datetime_created(model.datetime_created)
    # Idempotent: a re-delivered Telegram message reuses its meta row
    # instead of failing on the (lang, message_id, datetime_created) key.
    record = PhraseMeta.get(lang=lang, message_id=model.message_id, datetime_created=created)
    if not record:
        record = PhraseMeta(
            lang=lang,
            message_id=model.message_id,
            datetime_created=created,
            with_error=model.with_error,
        )
    return record.to_dict()
