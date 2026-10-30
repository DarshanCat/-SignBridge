import json

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from tests.helpers import valid_clip

client = TestClient(app)


def _override(tmp_path):
    app.dependency_overrides[get_settings] = lambda: Settings(
        model_dir=tmp_path / "models", animation_dir=tmp_path / "anims"
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_model_status_not_trained(tmp_path) -> None:
    _override(tmp_path)
    body = client.get("/api/model/status").json()
    assert body["state"] == "not_trained"
    assert body["loaded"] is False


def test_animations_empty(tmp_path) -> None:
    _override(tmp_path)
    body = client.get("/api/avatar/animations").json()
    assert body["count"] == 0


def test_animations_lists_real_files(tmp_path) -> None:
    (tmp_path / "anims").mkdir()
    (tmp_path / "anims" / "hello.json").write_text(json.dumps(valid_clip("HELLO")))
    (tmp_path / "anims" / "broken.json").write_text("{}")
    _override(tmp_path)
    body = client.get("/api/avatar/animations").json()
    assert body["animations"][0]["gloss"] == "HELLO" and body["count"] == 1
    assert len(body["invalid"]) == 1


def test_cors_allows_frontend_origin() -> None:
    r = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_blocks_other_origin() -> None:
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_oversized_request_body_is_rejected() -> None:
    big = {"frames": [], "pad": "x" * 2_100_000}
    r = client.post("/api/landmarks/extract", json=big)
    assert r.status_code == 413 and "too large" in r.json()["detail"]


def test_errors_do_not_leak_internals() -> None:
    r = client.post("/api/translation/english-to-gloss", content=b"{broken")
    assert r.status_code == 422 and "Traceback" not in r.text and "app/" not in r.text.replace("\\", "/")


def test_model_status_does_not_expose_absolute_paths(tmp_path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(model_dir=tmp_path / "models")
    body = client.get("/api/model/status").json()
    assert body["model_path"] == "models/isl_model.pt" and str(tmp_path) not in json.dumps(body)
