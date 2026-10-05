import asyncio
import re
from datetime import datetime, timezone
from types import SimpleNamespace

import fakeredis
import pytest
import requests
from telethon.tl.types import MessageMediaPhoto

from app.utils import Emoji
from conftest import PL_CHANNEL_ID, SU_ID


class FakeResponse:

    def __init__(self, status_code, text=''):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = text


class FakeEvent:

    def __init__(self, text='', chat_id=None, media=None):
        self.message = SimpleNamespace(
            message=text,
            id=7,
            media=media,
            date=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc),
        )
        self.peer_id = SimpleNamespace(user_id=SU_ID)
        self.chat_id = chat_id
        self.sent = []

    async def reply(self, text, **kwargs):
        self.sent.append(text)

    async def respond(self, text, **kwargs):
        self.sent.append(text)

    async def download_media(self, file=None):
        return b'image bytes'


class RecordingApiClient:

    def __init__(self, response):
        self.response = response
        self.calls = []

    def get_phrase(self, path, lang, params=None):
        self.calls.append((path, params))
        return self.response

    def delete_phrase(self, item_id, lang):
        self.calls.append(('delete', item_id))
        return self.response

    def post_phrase_meta(self, data, lang):
        self.calls.append(('meta', data))
        return self.response


@pytest.mark.parametrize('text, params', [
    ('/l', None),
    ('/l 200', {'tail': 200}),
    ('/l 200 5', {'tail': 200, 'count': 5}),
])
def test_tail_command_arguments(monkeypatch, bot_app, text, params):
    api = RecordingApiClient(FakeResponse(200, '[]'))
    monkeypatch.setattr(bot_app, 'api_client', api)

    asyncio.run(bot_app.handler_fetch_tail_pl(FakeEvent(text)))

    assert api.calls == [('fetch-tail', params)]


def test_tail_pattern_ignores_other_commands(bot_app):
    assert re.match(bot_app.FETCH_TAIL_RE, '/list') is None


def test_slice_pattern_rejects_extra_arguments(bot_app):
    assert re.match(bot_app.FETCH_SLICE_RE, '/s 1 2 3') is None


def test_delete_of_missing_phrase_reports_not_found(monkeypatch, bot_app):
    monkeypatch.setattr(bot_app, 'api_client', RecordingApiClient(FakeResponse(404)))
    event = FakeEvent('/d 999')

    asyncio.run(bot_app.handler_delete_record_by_id(event))

    assert event.sent == [f'Not Found {Emoji.CONFUSED_FACE}']


def test_photo_ingest_reports_redis_failure(monkeypatch, bot_app):
    server = fakeredis.FakeServer()
    server.connected = False
    monkeypatch.setattr(bot_app, 'api_client', RecordingApiClient(FakeResponse(200, '{}')))
    monkeypatch.setattr(bot_app, 'redis_client', fakeredis.FakeRedis(server=server))
    event = FakeEvent(chat_id=int(f'-100{PL_CHANNEL_ID}'), media=MessageMediaPhoto())

    assert asyncio.run(bot_app.handler_new_message_phrase(event)) is False
    assert event.sent and event.sent[-1].startswith('REDIS')


class FailingApiClient:

    def __getattr__(self, name):
        def call(*args, **kwargs):
            raise requests.ConnectionError('api down')
        return call


def test_photo_ingest_reports_api_outage(monkeypatch, bot_app):
    monkeypatch.setattr(bot_app, 'api_client', FailingApiClient())
    event = FakeEvent(chat_id=int(f'-100{PL_CHANNEL_ID}'), media=MessageMediaPhoto())

    assert asyncio.run(bot_app.handler_new_message_phrase(event)) is False
    assert event.sent and event.sent[-1].startswith('POST META')


def test_command_reports_api_outage(monkeypatch, bot_app):
    monkeypatch.setattr(bot_app, 'api_client', FailingApiClient())
    event = FakeEvent('/c 2')

    asyncio.run(bot_app.handler_fetch_count_pl(event))

    assert event.sent == [f'Server Error {Emoji.JACK_O_LANTERM}']
