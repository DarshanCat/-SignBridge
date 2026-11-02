"""Public deployment switches: recorder off, WebSocket origin check, CORS regex."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api import nlp_routes
from app.core.config import Settings, get_settings, origin_allowed
from app.main import app

client = TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_recorder_endpoints_are_off_when_disabled(tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(recording_enabled=False, record_dir=tmp_path / "rec")
    assert client.get("/api/record/plan").status_code == 403
    assert client.get("/api/record/takes", params={"signer_id": "P01"}).status_code == 403
    r = client.post("/api/record/sign", json={"gloss": "WHERE", "fps": 30, "frames": [{"pose": None, "left_hand": None, "right_hand": None}]})
    assert r.status_code == 403
    assert not (tmp_path / "rec").exists()  # nothing written


def test_recorder_is_on_by_default():
    app.dependency_overrides[get_settings] = lambda: Settings()
    assert client.get("/api/record/plan").status_code == 200


def test_origin_rule():
    s = Settings(cors_origins=["https://app.example"], cors_origin_regex=r"https://signbridge-.*\.vercel\.app")
    assert origin_allowed(None, s)  # not a browser
    assert origin_allowed("https://app.example", s)
    assert origin_allowed("https://signbridge-git-main-me.vercel.app", s)
    assert not origin_allowed("https://evil.example", s)
    assert not origin_allowed("https://signbridge-x.vercel.app.evil.example", s)  # the whole origin must match, not a prefix


def test_websocket_refuses_a_foreign_origin_when_the_check_is_on(monkeypatch):
    monkeypatch.setattr(nlp_routes, "get_settings", lambda: Settings(ws_check_origin=True, cors_origins=["https://app.example"]))
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/predict", headers={"origin": "https://evil.example"}):
            pass


def test_websocket_origin_check_is_off_by_default(monkeypatch):
    monkeypatch.setattr(nlp_routes, "get_settings", lambda: Settings(cors_origins=["https://app.example"]))
    with client.websocket_connect("/ws/predict", headers={"origin": "https://other.example"}) as ws:
        assert ws.receive_json()["type"] in ("ready", "error")


def test_cors_preflight_follows_the_regex(monkeypatch):
    # the middleware reads the settings once at import, so check the rule through the same helper the app uses
    s = Settings(cors_origin_regex=r"https://signbridge-.*\.vercel\.app")
    assert origin_allowed("https://signbridge-abc.vercel.app", s)
