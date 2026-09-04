import sqlite3

from fastapi import HTTPException, status
from pony.orm.core import CacheIndexError, TransactionIntegrityError


def is_phrase_unique_conflict(exc: Exception) -> bool:
    if isinstance(exc, CacheIndexError):
        return True
    message = str(getattr(exc, '__cause__', None) or exc)
    return (
        isinstance(exc, (TransactionIntegrityError, sqlite3.IntegrityError))
        and 'UNIQUE constraint failed' in message
    )


def phrase_db_http_exception(exc: Exception, lang: str) -> HTTPException:
    if isinstance(exc, CacheIndexError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f'Phrase already exists for lang={lang!r}: '
                'the same target and construction tag (target, target_tag) is already stored.'
            ),
        )

    message = str(getattr(exc, '__cause__', None) or exc)
    if isinstance(exc, (TransactionIntegrityError, sqlite3.IntegrityError)):
        if 'UNIQUE constraint failed' in message:
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f'Phrase already exists for lang={lang!r}: '
                    'a unique database constraint was violated.'
                ),
            )
        if 'FOREIGN KEY constraint failed' in message:
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f'Invalid phrase payload for lang={lang!r}: '
                    'a referenced record (e.g. meta_id) was not found.'
                ),
            )
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Database constraint violation for lang={lang!r}.',
        )

    if isinstance(exc, sqlite3.Error):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database error while saving phrase(s).',
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail='Unexpected error while saving phrase(s).',
    )
