from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Config(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=ROOT / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    frapper_username: str
    frapper_password: str

    sqlite_db_path: str
    frapper_api_port: int = 4040
    frapper_enable_docs: bool = False

    supported_langs: list[str] = ['pl', 'en']


config = Config()
