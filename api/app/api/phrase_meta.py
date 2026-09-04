from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pony.orm import db_session

from frapper_core.constants import DATETIME_FORMAT

from app.lang import LangQuery, validate_lang
from app.models.phrase_meta import PhraseMeta
from app.schemas.phrase_meta_schema import PhraseMetaSchema
from app.utils import validate_basic


router = APIRouter(prefix='/phrase-meta', tags=['phrase-meta'])


@router.get('', dependencies=[Depends(validate_basic)])
@db_session
def get_phrase_meta(
    lang: LangQuery,
    message_id: int = Query(...),
    datetime_created: str = Query(...),
):
    lang = validate_lang(lang)
    created = datetime.strptime(datetime_created, DATETIME_FORMAT)
    record = PhraseMeta.get(lang=lang, message_id=message_id, datetime_created=created)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Record not found')
    return record.to_dict()


@router.post('', dependencies=[Depends(validate_basic)])
@db_session
def post_phrase_meta(model: PhraseMetaSchema, lang: LangQuery):
    lang = validate_lang(lang)
    record = PhraseMeta(lang=lang, **model.model_dump())
    return record.to_dict()
