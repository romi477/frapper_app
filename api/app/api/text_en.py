from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.text_en_schema import TextEnCreate, TextEnResponse, TextEnSummary, TextEnUpdate
from app.services import text_en as text_en_service
from app.utils import validate_basic


router = APIRouter(prefix='/text-en', tags=['text-en'])


def _text_body_http_exception(exc: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


@router.post('', dependencies=[Depends(validate_basic)], response_model=TextEnResponse)
def create_text(model: TextEnCreate):
    try:
        return text_en_service.create_text(model.title, model.body, model.tags)
    except ValueError as exc:
        raise _text_body_http_exception(exc) from exc


@router.get('', dependencies=[Depends(validate_basic)], response_model=list[TextEnSummary])
def read_text_summaries(tag: Optional[str] = Query(default=None)):
    return text_en_service.read_text_summaries(tag)


@router.get('/{item_id}', dependencies=[Depends(validate_basic)], response_model=TextEnResponse)
def read_text(item_id: int):
    record = text_en_service.read_text_by_id(item_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Record not found')
    return record


@router.patch('/{item_id}', dependencies=[Depends(validate_basic)], response_model=TextEnResponse)
def patch_text(item_id: int, model: TextEnUpdate):
    if model.title is None and model.body is None and model.tags is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='At least one field must be provided',
        )
    try:
        record = text_en_service.update_text(item_id, model.title, model.body, model.tags)
    except ValueError as exc:
        raise _text_body_http_exception(exc) from exc
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Record not found')
    return record


@router.delete('/{item_id}', dependencies=[Depends(validate_basic)], response_model=dict)
def delete_text(item_id: int):
    if not text_en_service.delete_text(item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Record not found')
    return {'message': 'Record deleted successfully'}
