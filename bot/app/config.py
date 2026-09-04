from typing import Optional

from pydantic_settings import BaseSettings


class Config(BaseSettings):

    redis_host: str
    redis_port: int

    frapper_api_host: str
    frapper_api_port: int
    frapper_bot_token: str

    frapper_username: str
    frapper_password: str

    tg_frapper_id: int
    tg_phrase_pl_id: int
    tg_phrase_en_id: Optional[int] = None
    tg_api_id: int
    tg_su_id: int
    tg_api_hash: str


config = Config()
