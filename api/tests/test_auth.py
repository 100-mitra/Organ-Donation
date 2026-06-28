"""Access control on PII disclosure (/reveal) + allocator writes (D-022)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_reveal_is_open_in_demo_mode_when_no_token(monkeypatch):
    monkeypatch.delenv("ALLOCATOR_TOKEN", raising=False)
    assert TestClient(app).get("/reveal").status_code == 200


def test_reveal_requires_the_token_when_configured(monkeypatch):
    monkeypatch.setenv("ALLOCATOR_TOKEN", "s3cret")
    client = TestClient(app)
    assert client.get("/reveal").status_code == 401  # no token
    assert client.get("/reveal", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/reveal", headers={"Authorization": "Bearer s3cret"}).status_code == 200


def test_health_reports_auth_state(monkeypatch):
    monkeypatch.setenv("ALLOCATOR_TOKEN", "x")
    assert TestClient(app).get("/health").json()["auth_enabled"] is True
