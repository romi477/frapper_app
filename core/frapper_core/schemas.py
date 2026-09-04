from typing import List, Optional

from pydantic import BaseModel, Field, TypeAdapter, field_validator


class ItemMixin:

    @classmethod
    def post_keys_cls(cls):
        return tuple(cls.model_fields.keys())[1:-1]

    def post_data(self):
        return self.model_dump(exclude={'id', 'created_at'})


class PhraseMetaCreate(BaseModel):

    message_id: int
    datetime_created: str
    with_error: bool = False


class PhraseMetaResponse(PhraseMetaCreate, ItemMixin):

    _table_name = 'phrase_meta'

    id: int
    lang: str
    created_at: str


class PhraseCreate(BaseModel):

    meta_id: Optional[int] = None
    state: str = 'todo'
    active: bool
    target: str
    target_tag: str
    translate: str
    translate_tag: str
    target_mask: str
    translate_mask: str
    message_id: int
    message_date: str
    metadata: str


class PhraseResponse(PhraseCreate, ItemMixin):

    id: int
    created_at: str


PhraseList = TypeAdapter(List[PhraseResponse])


def _mask_word_count(text: str) -> int:
    return len(text.split())


class PhraseUpdate(BaseModel):
    target: str = Field(min_length=1)
    translate: str = Field(min_length=1)
    target_mask: str
    translate_mask: str

    @field_validator('target_mask')
    @classmethod
    def validate_target_mask(cls, value: str, info) -> str:
        target = info.data.get('target')
        if target is None:
            return value
        if not all(ch in '01' for ch in value):
            raise ValueError('target_mask must contain only 0 and 1')
        if len(value) != _mask_word_count(target):
            raise ValueError('target_mask length must match target word count')
        return value

    @field_validator('translate_mask')
    @classmethod
    def validate_translate_mask(cls, value: str, info) -> str:
        translate = info.data.get('translate')
        if translate is None:
            return value
        if not all(ch in '01' for ch in value):
            raise ValueError('translate_mask must contain only 0 and 1')
        if len(value) != _mask_word_count(translate):
            raise ValueError('translate_mask length must match translate word count')
        return value


# Backward-compatible aliases used by the API request layer.
PhraseMetaSchema = PhraseMetaCreate
PhraseSchema = PhraseCreate
