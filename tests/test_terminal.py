import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

import pytest
from fastapi.testclient import TestClient


def test_root_returns_html():
    from terminal.server import app
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_stream_endpoint_exists():
    from terminal.server import app
    routes = {r.path for r in app.routes}
    assert "/stream" in routes


def test_emit_event_adds_to_buffer():
    from terminal.server import emit_event, _event_buffer
    initial_len = len(_event_buffer)
    emit_event("SCRAPER", "test message", "run-001")
    assert len(_event_buffer) == initial_len + 1
    assert _event_buffer[-1]["agent"] == "SCRAPER"
    assert _event_buffer[-1]["message"] == "test message"
