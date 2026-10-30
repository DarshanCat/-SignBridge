import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.avatar.clip import BONES, ClipError, load_clip
from app.core.config import BACKEND_DIR, Settings, get_settings
from app.main import app
from tests.helpers import valid_clip

client = TestClient(app)


def write(tmp_path: Path, name: str, data: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return p


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_bone_list_matches_frontend_rig() -> None:
    frontend = json.loads((BACKEND_DIR.parent / "frontend" / "src" / "lib" / "avatar" / "bones.json").read_text())
    assert frontend == BONES


def test_valid_clip_loads(tmp_path) -> None:
    assert load_clip(write(tmp_path, "hello.json", valid_clip("HELLO"))).duration == 1.0


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda c: c["tracks"][0].update(bone="tail"), "unknown bone"),
        (lambda c: c.update(duration=0), "duration"),
        (lambda c: c["tracks"][0]["keyframes"][1].update(t=5), "past the clip duration"),
        (lambda c: c["tracks"][0]["keyframes"].reverse(), "time order"),
        (lambda c: c["tracks"][0]["keyframes"][0].update(rot=[0, 0]), "rot"),
        (lambda c: c.pop("source"), "source"),
        (lambda c: c.update(gloss="WATER"), "does not match"),
    ],
)
def test_invalid_clips_rejected(tmp_path, mutate, match) -> None:
    clip = valid_clip("HELLO")
    mutate(clip)
    with pytest.raises(ClipError, match=match):
        load_clip(write(tmp_path, "hello.json", clip))


def test_non_json_clip_rejected(tmp_path) -> None:
    (tmp_path / "x.json").write_text("nope")
    with pytest.raises(ClipError):
        load_clip(tmp_path / "x.json")


def test_vocabulary_endpoint_flags_animation_availability(tmp_path) -> None:
    anims = tmp_path / "a"
    anims.mkdir()
    write(anims, "hello.json", valid_clip("HELLO"))
    app.dependency_overrides[get_settings] = lambda: Settings(animation_dir=anims)
    body = client.get("/api/translation/vocabulary").json()
    by = {i["gloss"]: i["has_animation"] for i in body["items"]}
    assert by["HELLO"] is True and by["WATER"] is False and body["animated"] == 1
