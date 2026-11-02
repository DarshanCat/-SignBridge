"""Guided recording sessions with synthetic landmarks: folder layout per signer and gloss, the plan, resume counts and the new quality check."""

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.recording import PRIORITY_GLOSSES, clean_signer, count_takes, grammar_words, take_dir
from nlp.lexicon import load_lexicon
from tests.test_recording import frame, take

client = TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def post(tmp_path, frames, gloss, signer=None, make_clip=None, fps=30.0):
    app.dependency_overrides[get_settings] = lambda: Settings(record_dir=tmp_path / "rec")
    body = {"gloss": gloss, "fps": fps, "frames": frames}
    if signer is not None:
        body["signer_id"] = signer
    if make_clip is not None:
        body["make_clip"] = make_clip
    return client.post("/api/record/sign", json=body)


def hands_down_take(n: int = 40) -> list[dict]:
    """A body with the wrists resting low and still, and a hand detected next to the hip: nothing that looks like a sign."""
    out = []
    for _ in range(n):
        f = frame(0)
        f["pose"] = [dict(p) for p in f["pose"]]
        f["pose"][15] = {"x": 0.7, "y": 0.95, "z": 0.0}
        f["pose"][16] = {"x": 0.3, "y": 0.95, "z": 0.0}
        f["right_hand"] = [{"x": 0.3, "y": 0.97, "z": 0.0}] * 21
        out.append(f)
    return out


def test_plan_lists_the_grammar_words_priority_first() -> None:
    plan = client.get("/api/record/plan").json()
    assert plan["priority"] == PRIORITY_GLOSSES and plan["glosses"][:8] == PRIORITY_GLOSSES
    assert len(plan["glosses"]) == 50 and len(set(plan["glosses"])) == 50
    lex = load_lexicon()
    assert all(lex.signs[g].source != "include" for g in plan["glosses"])
    assert plan["glosses"][8:] == sorted(plan["glosses"][8:])


def test_signer_takes_go_to_signer_folder_without_a_clip_and_are_counted(tmp_path) -> None:
    for i in range(3):
        r = post(tmp_path, take(40 + i), "where", signer="p01", make_clip=False).json()
        assert r["accepted"] and r["signer_id"] == "P01" and r["clip"] is None and r["clip_file"] is None
        assert r["feature_file"].startswith("P01/WHERE/")
    post(tmp_path, take(40), "GO", signer="p01", make_clip=False)
    post(tmp_path, take(40), "WHERE", signer="p02", make_clip=False)
    folder = tmp_path / "rec" / "P01" / "WHERE"
    names = sorted(p.suffix for p in folder.iterdir())
    assert names.count(".npy") == 3 and names.count(".json") == 3 and ".webm" not in names  # no clip files, no video
    meta = json.loads(next(p for p in folder.glob("*.json")).read_text())
    assert meta["signer_id"] == "P01" and meta["contains_video"] is False
    assert count_takes(tmp_path / "rec", "P01") == {"GO": 1, "WHERE": 3}
    assert count_takes(tmp_path / "rec", "P99") == {}
    app.dependency_overrides[get_settings] = lambda: Settings(record_dir=tmp_path / "rec")
    got = client.get("/api/record/takes", params={"signer_id": "p01"}).json()
    assert got == {"signer_id": "P01", "counts": {"GO": 1, "WHERE": 3}, "total": 4}


def test_without_a_signer_id_the_old_layout_and_clip_still_work(tmp_path) -> None:
    r = post(tmp_path, take(40), "water").json()
    assert r["accepted"] and r["signer_id"] is None and r["clip"] is not None and r["feature_file"].startswith("WATER/")
    assert take_dir(tmp_path, "WATER") == tmp_path / "WATER"


@pytest.mark.parametrize("bad", ["../x", "a/b", "a b", "", "-x", "A" * 40, "é"])
def test_bad_signer_ids_are_rejected_and_nothing_is_written(tmp_path, bad) -> None:
    r = post(tmp_path, take(40), "WHERE", signer=bad)
    assert r.status_code == 422
    assert not (tmp_path / "rec").exists()
    with pytest.raises(ValueError):
        clean_signer(bad)


def test_a_take_without_any_sign_movement_is_rejected_and_not_stored(tmp_path) -> None:
    r = post(tmp_path, hands_down_take(), "WHERE", signer="P01", make_clip=False).json()
    assert not r["accepted"] and not r["saved"] and any("No sign movement" in m for m in r["reasons"])
    assert not (tmp_path / "rec").exists()


def test_a_good_take_has_exactly_one_segment_recorded_in_its_stats(tmp_path) -> None:
    r = post(tmp_path, take(45), "WHERE", signer="P01", make_clip=False).json()
    assert r["accepted"] and r["stats"]["segments"] == 1


def test_a_whole_guided_session_with_synthetic_landmarks(tmp_path) -> None:
    """Two signers, three glosses, up to 4 takes each; one take per gloss is deliberately bad. Rejected takes are never counted or stored."""
    glosses = ["WHERE", "GO", "LIKE"]
    for signer in ("P01", "P02"):
        for g in glosses:
            accepted = 0
            attempts = 0
            while accepted < 4 and attempts < 8:
                attempts += 1
                frames = hands_down_take() if attempts == 2 else take(36 + attempts)  # the second attempt of every gloss is a bad take
                r = post(tmp_path, frames, g, signer=signer, make_clip=False).json()
                accepted += r["accepted"]
            assert accepted == 4 and attempts == 5
    for signer in ("P01", "P02"):
        assert count_takes(tmp_path / "rec", signer) == {"GO": 4, "LIKE": 4, "WHERE": 4}
    files = sorted(p.relative_to(tmp_path / "rec").parts[:2] for p in (tmp_path / "rec").rglob("*.npy"))
    assert len(files) == 24 and {f[0] for f in files} == {"P01", "P02"}
    arr = np.load(next((tmp_path / "rec" / "P01" / "GO").glob("*.npy")))
    assert arr.ndim == 2 and arr.shape[1] == 225


def test_grammar_words_helper_matches_the_dictionary() -> None:
    lex = load_lexicon()
    words = grammar_words(lex)
    assert words[:8] == PRIORITY_GLOSSES and set(words) == {g for g, s in lex.signs.items() if s.source != "include"}
