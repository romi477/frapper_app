import os
import sys
from pathlib import Path

import pytest
import telethon.sync

BOT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOT_ROOT))

SU_ID = 42
PL_CHANNEL_ID = 1001

os.environ.update(
    REDIS_HOST='redis.test',
    REDIS_PORT='6379',
    FRAPPER_API_HOST='api.test',
    FRAPPER_API_PORT='4040',
    FRAPPER_BOT_TOKEN='test-token',
    FRAPPER_USERNAME='test-user',
    FRAPPER_PASSWORD='test-password',
    TG_PHRASE_PL_ID=str(PL_CHANNEL_ID),
    TG_API_ID='1',
    TG_SU_ID=str(SU_ID),
    TG_API_HASH='test-hash',
)


class FakeTelegramClient:
    """Stands in for Telethon's client: app.bot creates one (and its session file) at import."""

    def __init__(self, *args, **kwargs):
        pass

    def on(self, event):
        return lambda handler: handler


telethon.sync.TelegramClient = FakeTelegramClient


@pytest.fixture
def bot_app():
    from app import bot

    return bot
