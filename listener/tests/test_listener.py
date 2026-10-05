import fakeredis
import pytest
import requests

from app import listener

KEY = 'pl_7_2026-10-01T10:00:00'


class FakeResponse:

    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload if payload is not None else {}
        self.text = str(self._payload)

    def json(self):
        return self._payload


class StubApiClient:

    def __init__(self, meta_response=None, error=None):
        self.meta_response = meta_response
        self.error = error

    def get_phrase_meta(self, lang, message_id, datetime_created):
        if self.error:
            raise self.error
        return self.meta_response

    def post_phrase(self, data, lang):
        return FakeResponse(200, [])


@pytest.fixture
def server():
    return fakeredis.FakeServer()


@pytest.fixture
def db0(server):
    return fakeredis.FakeRedis(server=server, db=0)


@pytest.fixture
def db1(server):
    return fakeredis.FakeRedis(server=server, db=1)


def test_unreadable_image_is_parked_in_db1(monkeypatch, db0, db1):
    db0.set(KEY, b'not an image')
    monkeypatch.setattr(listener, 'api_client', StubApiClient(meta_response=FakeResponse(200, {'id': 1})))

    listener.read_redis_db(db0)

    assert db0.get(KEY) is None
    assert db1.get(KEY) == b'not an image'


def test_api_outage_keeps_key_queued_for_retry(monkeypatch, db0, db1):
    db0.set(KEY, b'image bytes')
    monkeypatch.setattr(listener, 'api_client', StubApiClient(error=requests.ConnectionError('api down')))

    listener.read_redis_db(db0)

    assert db0.get(KEY) == b'image bytes'
    assert db1.get(KEY) is None


def test_failed_key_replaces_stale_copy_in_db1(monkeypatch, db0, db1):
    db0.set(KEY, b'new bytes')
    db1.set(KEY, b'old bytes')
    monkeypatch.setattr(listener, 'api_client', StubApiClient(meta_response=FakeResponse(404)))

    listener.read_redis_db(db0)

    assert db0.get(KEY) is None
    assert db1.get(KEY) == b'new bytes'


def test_poll_once_survives_redis_outage(server, db0):
    server.connected = False

    listener.poll_once(db0)
