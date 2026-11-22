"""The Docker probe must reject failed HTTP responses and unready models."""

from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest


class Response(BytesIO):
    def __init__(self, body, status=200):
        super().__init__(body)
        self.status = status


@pytest.mark.parametrize(
    ("body", "status", "healthy"),
    [
        (b'{"status":"healthy","model_loaded":true}', 200, True),
        (b'{"status":"healthy","model_loaded":false}', 200, False),
        (b'{"status":"healthy","model_loaded":"true"}', 200, False),
        (b'{"status":"starting","model_loaded":true}', 200, False),
        (b'{"status":"healthy","model_loaded":true}', 503, False),
        (b'{"status":"healthy"}', 200, False),
        (b'[]', 200, False),
        (b'not JSON', 200, False),
    ],
)
def test_probe_requires_a_healthy_loaded_model(healthcheck, monkeypatch, body, status, healthy):
    def fake_open(url, timeout):
        assert url == "http://127.0.0.1:8000/health"
        assert 0 < timeout <= 2
        return Response(body, status)

    monkeypatch.setattr(healthcheck, "urlopen", fake_open)
    assert healthcheck.is_healthy() is healthy


@pytest.mark.parametrize(
    "error",
    [URLError("connection refused"), TimeoutError("timed out"),
     HTTPError("http://127.0.0.1:8000/health", 503, "Unavailable", {}, None)],
)
def test_unavailable_api_is_unhealthy(healthcheck, monkeypatch, error):
    def failed_open(url, timeout):
        raise error

    monkeypatch.setattr(healthcheck, "urlopen", failed_open)
    assert healthcheck.is_healthy() is False
