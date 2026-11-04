"""Conversation vocabulary: the data file agrees with the model's class list, the preset lists only what must be recorded, the endpoints answer."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.conversation_vocab import load_vocabulary
from app.main import app

client = TestClient(app)
LABELS = Path(__file__).resolve().parents[1] / "models" / "labels.json"
needs_model = pytest.mark.skipif(not LABELS.is_file(), reason="models/labels.json is git-ignored and absent")


def test_vocabulary_shape_and_counts() -> None:
    v = load_vocabulary()
    assert len(v.signs) == 40 and len(v.test_sentences) == 10
    assert len(v.known()) == 9 and len(v.to_record()) == 31
    assert set(v.known()) | set(v.to_record()) == {s.gloss for s in v.signs}
    for g in ["WHAT", "WHERE", "HOW", "WHO", "WHEN", "WHY", "I", "YOU", "HE", "SHE", "WE", "DO", "GO", "COME", "EAT", "DRINK", "WANT", "LIKE", "KNOW",
              "HELP", "WORK", "NAME", "YES", "NO", "GOOD", "BAD", "OK", "THANK-YOU", "SORRY", "PLEASE", "HELLO", "BYE"]:
        assert g in {s.gloss for s in v.signs}  # every sign of the request


@needs_model
def test_known_signs_are_real_include_classes_and_the_rest_are_not() -> None:
    classes = set(json.loads(LABELS.read_text(encoding="utf-8"))["classes"])
    from nlp.gloss_forms import to_gloss

    glosses = {to_gloss(c) for c in classes}
    for s in load_vocabulary().signs:
        if s.include_class is not None:
            assert s.include_class in classes and to_gloss(s.include_class) == s.gloss
        else:
            assert s.gloss not in glosses  # a sign marked "to record" is not an INCLUDE class under the same gloss


def test_conversation_preset_lists_only_signs_to_record() -> None:
    plan = client.get("/api/record/plan", params={"preset": "conversation"}).json()
    assert plan["glosses"] == load_vocabulary().to_record() and len(plan["glosses"]) == 31
    assert not {"HELLO", "I", "YOU", "GOOD", "THANK-YOU"} & set(plan["glosses"])
    assert client.get("/api/record/plan", params={"preset": "nope"}).status_code == 422
    assert len(client.get("/api/record/plan").json()["glosses"]) == 50  # the default list is unchanged


def test_vocabulary_endpoint() -> None:
    body = client.get("/api/conversation/vocabulary").json()
    assert body["known"] == 9 and body["to_record"] == 31 and len(body["signs"]) == 40 and len(body["test_sentences"]) == 10


@needs_model
def test_model_signs_endpoint_lists_every_class() -> None:
    body = client.get("/api/model/signs").json()
    assert body["loaded"] and body["count"] == len(json.loads(LABELS.read_text(encoding="utf-8"))["classes"])
    assert {"Hello", "Thank you"} <= {s["label"] for s in body["signs"]}
