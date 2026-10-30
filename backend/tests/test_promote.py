import json
from pathlib import Path

import pytest

from app.avatar.sign_registry import build_report
from retarget.promote import PromoteError, promote
from tests.helpers import valid_clip


def setup(tmp_path: Path, gloss: str = "WATER", **source) -> tuple[Path, Path, Path]:
    clip = valid_clip(gloss)
    clip["source"].update({"review_status": "not_signer_reviewed", "origin": "self-recorded", "source_sample": {"kind": "self-recorded", "feature_file": "t.npy"}, **source})
    cp = tmp_path / "take.clip.json"
    cp.write_text(json.dumps(clip))
    anims = tmp_path / "anims"
    anims.mkdir()
    reg = tmp_path / "reg.json"
    reg.write_text(json.dumps({"_notice": "keep me", "signs": [{"gloss": "WATER", "meaning": "water", "context": "placeholder", "verification_status": "no_clip"}]}))
    return cp, anims, reg


def test_promote_copies_indexes_registers_and_stays_unreviewed(tmp_path) -> None:
    cp, anims, reg = setup(tmp_path)
    r = promote(cp, anims, reg)
    assert r["replaced"] is False
    assert json.loads((anims / "water.json").read_text())["source"]["review_status"] == "not_signer_reviewed"
    idx = json.loads((anims / "index.json").read_text())["clips"]["WATER"]
    assert idx["file"] == "water.json" and idx["origin"] == "self-recorded" and idx["review_status"] == "not_signer_reviewed"
    saved = json.loads(reg.read_text())
    assert saved["_notice"] == "keep me"
    rec = saved["signs"][0]
    assert rec["asset_id"] == "water" and rec["verification_status"] == "clip_unreviewed" and not rec["signer_reviewed"]
    report = build_report(reg, anims)
    assert report.signs[0].status == "clip_unreviewed" and report.unregistered_clips == [] and report.totals["verified"] == 0


def test_new_gloss_gets_a_registry_record(tmp_path) -> None:
    cp, anims, reg = setup(tmp_path, "NEWSIGN")
    promote(cp, anims, reg, meaning="a new sign")
    glosses = {s["gloss"]: s for s in json.loads(reg.read_text())["signs"]}
    assert glosses["NEWSIGN"]["meaning"] == "a new sign" and glosses["NEWSIGN"]["asset_id"] == "newsign"


def test_refuses_existing_gloss_unless_replace_and_changes_nothing_when_refused(tmp_path) -> None:
    cp, anims, reg = setup(tmp_path)
    promote(cp, anims, reg)
    before = {p.name: p.read_bytes() for p in [anims / "water.json", anims / "index.json", reg]}
    with pytest.raises(PromoteError, match="already has a clip"):
        promote(cp, anims, reg)
    assert before == {p.name: p.read_bytes() for p in [anims / "water.json", anims / "index.json", reg]}
    assert promote(cp, anims, reg, replace=True)["replaced"] is True


def test_refuses_a_clip_that_claims_signer_review_and_invalid_clips(tmp_path) -> None:
    cp, anims, reg = setup(tmp_path, review_status="signer_reviewed")
    with pytest.raises(PromoteError, match="not_signer_reviewed"):
        promote(cp, anims, reg)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"gloss": "X"}))
    with pytest.raises(PromoteError):
        promote(bad, anims, reg)
    assert not (anims / "water.json").exists()


def test_dry_run_writes_nothing(tmp_path) -> None:
    cp, anims, reg = setup(tmp_path)
    before = reg.read_bytes()
    assert promote(cp, anims, reg, dry_run=True)["dry_run"] is True
    assert not (anims / "water.json").exists() and reg.read_bytes() == before
