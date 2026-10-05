import socket
import threading
import time

import pytest
import requests

from frapper_core import FrapperApiClient


@pytest.fixture
def silent_server():
    """Accepts connections and never answers, like a hung API."""
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen()
    connections = []

    def accept():
        try:
            while True:
                connections.append(sock.accept()[0])
        except OSError:
            pass

    threading.Thread(target=accept, daemon=True).start()
    yield f'http://127.0.0.1:{sock.getsockname()[1]}'
    sock.close()
    for conn in connections:
        conn.close()


def test_requests_time_out_instead_of_hanging(silent_server):
    client = FrapperApiClient(silent_server, 'user', 'password', timeout=0.5)
    started = time.monotonic()

    with pytest.raises(requests.Timeout):
        client.get_phrase_meta('pl', 1, '2026-10-01T10:00:00')

    assert time.monotonic() - started < 5


def test_default_timeout_is_finite():
    client = FrapperApiClient('http://api.test:4040', 'user', 'password')

    assert 0 < client.timeout <= 60
