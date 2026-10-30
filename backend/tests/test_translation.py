import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import BACKEND_DIR, Settings, get_settings
from app.main import app
from tests.helpers import valid_clip
from app.translation.english_to_gloss import english_to_gloss
from app.translation.gloss_to_english import gloss_to_english
from app.translation.labels import labels_to_gloss, normalize_gloss
from app.translation.vocabulary import VocabularyError, load_vocabulary

client = TestClient(app)
VOCAB = load_vocabulary(BACKEND_DIR / "config" / "translation.json")


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_default_vocabulary_loads_and_is_flagged_as_placeholder() -> None:
    raw = json.loads((BACKEND_DIR / "config" / "translation.json").read_text(encoding="utf-8"))
    assert "NOT been validated" in raw["_notice"]
    assert "HELLO" in VOCAB.glosses


def test_english_to_gloss_drops_stopwords_and_maps() -> None:
    r = english_to_gloss("Hello, I need the water", VOCAB)
    assert r.gloss == ["HELLO", "I", "WATER"]
    assert "need" in r.unsupported
    assert [w.status for w in r.words if w.word == "the"] == ["dropped"]


def test_english_to_gloss_phrase_and_question_reordering() -> None:
    assert english_to_gloss("thank you", VOCAB).gloss == ["THANK-YOU"]
    r = english_to_gloss("What is your name?", VOCAB)
    assert r.gloss == ["YOU", "NAME", "WHAT"]
    assert r.coverage == 1.0 and r.unsupported == []


def test_english_to_gloss_unsupported_and_coverage() -> None:
    r = english_to_gloss("quantum helps", VOCAB)
    assert r.gloss == ["HELP"] and r.unsupported == ["quantum"] and r.coverage == 0.5
    none = english_to_gloss("xyzzy plugh", VOCAB)
    assert none.gloss == [] and none.coverage == 0.0


def test_english_to_gloss_rejects_wordless_text() -> None:
    with pytest.raises(ValueError):
        english_to_gloss("?!... 123", VOCAB)


def test_gloss_to_english_phrase_tokens_and_unknown() -> None:
    assert gloss_to_english(["you", "name", "what"], VOCAB).english == "What is your name?"
    r = gloss_to_english(["HELLO", "FLY", "WATER"], VOCAB)
    assert r.english == "Hello water." and r.unsupported == ["FLY"]
    assert gloss_to_english(["FLY"], VOCAB).english == ""


def test_label_normalization() -> None:
    assert normalize_gloss([" thank you ", "thank_you", "HELLO", "", "hello"]) == ["THANK-YOU", "HELLO"]
    gloss, unknown = labels_to_gloss(["hello", "zzz"], VOCAB)
    assert gloss == ["HELLO", "ZZZ"] and unknown == ["ZZZ"]


def test_bad_vocabulary_files(tmp_path) -> None:
    with pytest.raises(VocabularyError):
        load_vocabulary(tmp_path / "missing.json")
    bad = tmp_path / "v.json"
    bad.write_text('{"glosses": {}}')
    with pytest.raises(VocabularyError):
        load_vocabulary(bad)
    bad.write_text("not json")
    with pytest.raises(VocabularyError):
        load_vocabulary(bad)


def test_custom_vocabulary_is_configurable(tmp_path) -> None:
    cfg = tmp_path / "v.json"
    cfg.write_text(json.dumps({"glosses": {"cat": {"english": "cat", "words": ["cat", "cats"]}}}))
    r = english_to_gloss("cats", load_vocabulary(cfg))
    assert r.gloss == ["CAT"]


def test_api_english_to_gloss() -> None:
    r = client.post("/api/translation/english-to-gloss", json={"text": "hello water please"})
    body = r.json()
    assert r.status_code == 200 and body["gloss"] == ["HELLO", "WATER"] and "placeholder" in body["note"]


def test_api_validation_errors() -> None:
    assert client.post("/api/translation/english-to-gloss", json={"text": ""}).status_code == 422
    assert client.post("/api/translation/english-to-gloss", json={"text": "123"}).status_code == 422
    assert client.post("/api/translation/gloss-to-english", json={"gloss": []}).status_code == 422
    assert client.post("/api/translation/english-to-gloss", json={"text": "a" * 501}).status_code == 422


def test_api_gloss_to_english() -> None:
    body = client.post("/api/translation/gloss-to-english", json={"gloss": ["hello", "you"]}).json()
    assert body["english"] == "Hello you."


def test_api_503_when_vocabulary_missing(tmp_path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(translation_config=tmp_path / "nope.json")
    assert client.post("/api/translation/english-to-gloss", json={"text": "hello"}).status_code == 503


def test_avatar_plan_marks_missing_clips(tmp_path) -> None:
    anims = tmp_path / "anims"
    anims.mkdir()
    (anims / "hello.json").write_text(json.dumps(valid_clip("HELLO")))
    app.dependency_overrides[get_settings] = lambda: Settings(animation_dir=anims)
    body = client.post("/api/avatar/plan", json={"gloss": ["hello", "water"]}).json()
    assert [s["available"] for s in body["steps"]] == [True, False]
    assert body["missing"] == ["WATER"] and body["playable"] is False
    full = client.post("/api/avatar/plan", json={"gloss": ["hello"]}).json()
    assert full["playable"] is True and full["steps"][0]["clip_url"] == "/animations/hello.json"


def test_avatar_plan_with_no_clips_is_not_playable(tmp_path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(animation_dir=tmp_path / "none")
    body = client.post("/api/avatar/plan", json={"gloss": ["hello"]}).json()
    assert body["playable"] is False and "nothing can be played" in body["message"]
