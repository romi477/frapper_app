import sqlite3
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pony.orm.core import CacheIndexError, TransactionIntegrityError

from app.db.errors import is_phrase_unique_conflict, phrase_db_http_exception
from app.lang import LangQuery
from app.services import phrase as phrase_service
from app.schemas.phrase_schema import PhraseSchema
from app.schemas.phrase_update_schema import PhraseUpdate
from app.utils import validate_basic


router = APIRouter(prefix='/phrase', tags=['phrase'])


@router.post('/manual', dependencies=[Depends(validate_basic)], response_model=dict)
def create_phrase_manual(model: PhraseUpdate, lang: LangQuery):
    try:
        return phrase_service.create_phrase(
            lang,
            model.target,
            model.translate,
            model.target_mask,
            model.translate_mask,
        )
    except (CacheIndexError, TransactionIntegrityError, sqlite3.Error) as exc:
        raise phrase_db_http_exception(exc, lang) from exc


@router.post('/manual/bulk', dependencies=[Depends(validate_basic)], response_model=list)
def create_phrases_manual(models: List[PhraseUpdate], lang: LangQuery):
    created = []
    for model in models:
        try:
            created.append(
                phrase_service.create_phrase(
                    lang,
                    model.target,
                    model.translate,
                    model.target_mask,
                    model.translate_mask,
                )
            )
        except (CacheIndexError, TransactionIntegrityError, sqlite3.Error) as exc:
            if is_phrase_unique_conflict(exc):
                created.append({})
                continue
            raise phrase_db_http_exception(exc, lang) from exc
    return created


@router.post('', dependencies=[Depends(validate_basic)], response_model=list)
def post_phrase(model_list: List[PhraseSchema], lang: LangQuery):
    try:
        return phrase_service.post_phrases(model_list, lang)
    except (CacheIndexError, TransactionIntegrityError, sqlite3.Error) as exc:
        raise phrase_db_http_exception(exc, lang) from exc


@router.get('/target-tag', dependencies=[Depends(validate_basic)], response_model=list)
def read_target_tag(lang: LangQuery, tag: str = None):
    return phrase_service.read_target_tag(lang, tag)


@router.get('/translate-tag', dependencies=[Depends(validate_basic)], response_model=list)
def read_translate_tag(lang: LangQuery, tag: str = None):
    return phrase_service.read_translate_tag(lang, tag)


@router.get('/stats', dependencies=[Depends(validate_basic)], response_model=dict)
def read_phrase_stats():
    return phrase_service.read_phrase_stats()


@router.get('/fetch-count', dependencies=[Depends(validate_basic)], response_model=list)
def read_target_count(lang: LangQuery, count: int = 10):
    return phrase_service.read_target_count(lang, count)


@router.get('/fetch-slice', dependencies=[Depends(validate_basic)], response_model=list)
def read_target_slice(lang: LangQuery, since_id: int, count: int = 10):
    return phrase_service.read_target_slice(lang, since_id, count)


@router.get('/fetch-tail', dependencies=[Depends(validate_basic)], response_model=list)
def read_target_from_tail(
    lang: LangQuery,
    tail: int = Query(100, ge=1, description='How many recent rows form the tail pool'),
    count: int = Query(10, ge=1, description='How many random phrases to return'),
):
    return phrase_service.read_target_from_tail(lang, tail, count)


@router.get('/fetch-date', dependencies=[Depends(validate_basic)], response_model=list)
def read_phrases_by_date(lang: LangQuery, date: date):
    return phrase_service.read_phrases_by_date(lang, date)


@router.get('/date-count', dependencies=[Depends(validate_basic)], response_model=dict)
def read_phrase_count_by_date(lang: LangQuery, date: date):
    return {'count': phrase_service.count_phrases_by_date(lang, date)}


@router.get('/{item_id}', dependencies=[Depends(validate_basic)], response_model=list)
def read_phrase(item_id: int, lang: LangQuery):
    return phrase_service.read_phrase_by_id(lang, item_id)


@router.patch('/{item_id}', dependencies=[Depends(validate_basic)], response_model=dict)
def patch_phrase(item_id: int, model: PhraseUpdate, lang: LangQuery):
    try:
        record = phrase_service.update_phrase(
            lang,
            item_id,
            model.target,
            model.translate,
            model.target_mask,
            model.translate_mask,
        )
    except (CacheIndexError, TransactionIntegrityError, sqlite3.Error) as exc:
        raise phrase_db_http_exception(exc, lang) from exc
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Record not found')
    return record


@router.delete('/{item_id}', dependencies=[Depends(validate_basic)], response_model=dict)
def delete_phrase(item_id: int, lang: LangQuery):
    return phrase_service.delete_phrase(lang, item_id)
