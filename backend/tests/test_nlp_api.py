import pytest
from fastapi.testclient import TestClient

from app.api import nlp_routes
from app.core.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_text_to_gloss_endpoint_returns_gloss_markers_and_notes() -> None:
    r = client.post("/api/nlp/text-to-gloss", json={"text": "I went to the market yesterday."})
    body = r.json()
    assert r.status_code == 200
    assert body["gloss"] == ["YESTERDAY", "I", "MARKET", "GO"] and body["tense"] == "past"
    assert "not validated" in body["note"]
    q = client.post("/api/nlp/text-to-gloss", json={"text": "Where is the hospital?"}).json()
    assert q["gloss"] == ["HOSPITAL", "WHERE"] and q["nmm"] == ["wh-question"]
    fs = client.post("/api/nlp/text-to-gloss", json={"text": "My name is Ravi."}).json()
    assert fs["fingerspelled"] == ["RAVI"] and fs["tokens"][-1]["letters"] == ["R", "A", "V", "I"]


def test_gloss_to_text_endpoint() -> None:
    r = client.post("/api/nlp/gloss-to-text", json={"gloss": ["YESTERDAY", "I", "MARKET", "GO"]})
    assert r.status_code == 200 and r.json()["english"] == "I went to the market yesterday."


@pytest.mark.parametrize("path, body", [
    ("/api/nlp/text-to-gloss", {"text": ""}), ("/api/nlp/text-to-gloss", {"text": "?!..."}), ("/api/nlp/text-to-gloss", {"text": "a" * 501}),
    ("/api/nlp/gloss-to-text", {"gloss": []}), ("/api/nlp/gloss-to-text", {"gloss": ["   "]}),
])
def test_invalid_input_is_422(path, body) -> None:
    assert client.post(path, json=body).status_code == 422


def test_missing_spacy_model_or_dictionary_is_503(tmp_path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(spacy_model="no_such_model_installed")
    nlp_routes._load_nlp.cache_clear()
    r = client.post("/api/nlp/text-to-gloss", json={"text": "hello"})
    assert r.status_code == 503 and "not installed" in r.json()["detail"]
    app.dependency_overrides[get_settings] = lambda: Settings(gloss_dictionary=tmp_path / "missing.json")
    assert client.post("/api/nlp/gloss-to-text", json={"gloss": ["HELLO"]}).status_code == 503
    nlp_routes._load_nlp.cache_clear()


def test_websocket_predict_reports_model_not_trained_and_closes(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(nlp_routes, "get_settings", lambda: Settings(model_dir=tmp_path / "none"))
    with client.websocket_connect("/ws/predict") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error" and msg["error"] == "model_not_trained" and "prediction" not in msg
        with pytest.raises(Exception):  # the server closes with 1013 right after the error
            ws.receive_json()
