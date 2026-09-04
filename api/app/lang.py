from typing import Annotated

from fastapi import HTTPException, Query, status

from app.config import config
from app.models.phrase_en import PhraseEn
from app.models.phrase_pl import PhrasePl


PHRASE_ENTITIES = {
    'pl': PhrasePl,
    'en': PhraseEn,
}

LangQuery = Annotated[str, Query(..., description=f'Language code ({", ".join(config.supported_langs)})')]


def validate_lang(lang: str) -> str:
    lang = lang.lower()
    if lang not in config.supported_langs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported lang {lang!r}. Supported: {sorted(config.supported_langs)}',
        )
    return lang


def get_phrase_entity(lang: str):
    return PHRASE_ENTITIES[validate_lang(lang)]
