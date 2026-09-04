# python3

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import config


_get_basic_credentials = HTTPBasic()


def validate_basic(credentials: HTTPBasicCredentials = Depends(_get_basic_credentials)) -> str:
    correct_username = secrets.compare_digest(
        credentials.username.encode('utf8'),
        config.frapper_username.encode('utf8'),
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode('utf8'),
        config.frapper_password.encode('utf8'),
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials',
            headers={'WWW-Authenticate': 'Basic'},
        )

    return credentials.username
