import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.avatar.sign_registry import RegistryError, build_report, load_registry
from app.core.config import BACKEND_DIR, Settings, get_settings
from app.main import app
from app.translation.vocabulary import load_vocabulary
from tests.helpers import valid_clip

client = TestClient(app)
SHIPPED_REGISTRY = BACKEND_DIR / "config" / "sign_registry.json"
SHIPPED_ANIMATIONS = BACKEND_DIR.parent / "frontend" / "public" / "animations"


def teardown_function() -> None:
    app.dependency_overrides.clear()


def record(gloss: str, **kw) -> dict:
    base = {"gloss": gloss, "meaning": gloss.lower(), "context": "test", "verification_status": "no_clip"}
    return {**base, **kw}


def setup(tmp_path: Path, signs: list[dict], clips: dict[str, dict] | None = None) -> tuple[Path, Path]:
    reg = tmp_path / "reg.json"
    reg.write_text(json.dumps({"signs": signs}))
    anims = tmp_path / "anims"
    anims.mkdir()
    for stem, data in (clips or {}).items():
        (anims / f"{stem}.json").write_text(json.dumps(data))
    return reg, anims


FULL = {"reference_source": "ref", "license": "CC BY 4.0", "attribution": "someone"}


def test_shipped_registry_covers_the_vocabulary_and_only_known_glosses() -> None:
    import json

    vocab = load_vocabulary(BACKEND_DIR / "config" / "translation.json")
    dictionary = json.loads((BACKEND_DIR / "config" / "gloss_dictionary.json").read_text(encoding="utf-8"))["signs"]
    glosses = {s.gloss for s in load_registry(SHIPPED_REGISTRY).signs}
    assert set(vocab.glosses) <= glosses  # every placeholder vocabulary gloss has a registry record
    assert glosses <= set(vocab.glosses) | set(dictionary)  # and nothing unknown is registered


def test_shipped_clips_are_all_registered_valid_and_none_is_claimed_verified() -> None:
    report = build_report(SHIPPED_REGISTRY, SHIPPED_ANIMATIONS)
    assert report.unregistered_clips == []
    assert all(not s.problems for s in report.signs)
    assert report.totals["verified"] == 0 and report.totals["missing_asset"] == 0
    clips = [p for p in SHIPPED_ANIMATIONS.glob("*.json") if p.name != "index.json"]
    assert report.totals["clip_unreviewed"] == len(clips)
    for p in clips:  # every shipped clip says it is not signer reviewed
        assert json.loads(p.read_text(encoding="utf-8"))["source"]["review_status"] == "not_signer_reviewed"


def test_status_progression(tmp_path) -> None:
    reg, anims = setup(
        tmp_path,
        [
            record("NONE"),
            record("RAW", asset_id="raw"),  # clip, no provenance
            record("REVIEWED", asset_id="reviewed", visually_reviewed=True, signer_reviewed=True, **FULL),
            record("HALF", asset_id="half", visually_reviewed=True, **FULL),
        ],
        {"raw": valid_clip("RAW"), "reviewed": valid_clip("REVIEWED"), "half": valid_clip("HALF")},
    )
    by = {s.gloss: s for s in build_report(reg, anims).signs}
    assert by["NONE"].status == "no_clip"
    assert by["RAW"].status == "clip_unreviewed" and by["RAW"].problems
    assert by["HALF"].status == "clip_unreviewed" and not by["HALF"].problems
    assert by["REVIEWED"].status == "verified"


def test_unearned_verified_claim_missing_invalid_and_unregistered(tmp_path) -> None:
    reg, anims = setup(
        tmp_path,
        [
            record("LIAR", asset_id="liar", verification_status="verified", **FULL),
            record("GONE", asset_id="gone"),
            record("BAD", asset_id="bad"),
            record("MISMATCH", asset_id="mismatch", visually_reviewed=True, signer_reviewed=True, **FULL),
        ],
        {"liar": valid_clip("LIAR"), "bad": {"gloss": "BAD"}, "mismatch": valid_clip("OTHER"), "orphan": valid_clip("ORPHAN")},
    )
    report = build_report(reg, anims)
    by = {s.gloss: s for s in report.signs}
    assert by["LIAR"].status == "clip_unreviewed" and "claims verified" in " ".join(by["LIAR"].problems)
    assert by["GONE"].status == "missing_asset" and by["BAD"].status == "missing_asset"
    assert by["MISMATCH"].status != "verified" or by["MISMATCH"].problems  # loader rejects the mismatched gloss
    assert report.unregistered_clips == ["orphan"]


def test_duplicate_and_unreadable_registry(tmp_path) -> None:
    reg, _ = setup(tmp_path, [record("A"), record("a")])
    with pytest.raises(RegistryError, match="duplicate"):
        load_registry(reg)
    with pytest.raises(RegistryError):
        load_registry(tmp_path / "missing.json")


def test_registry_endpoint(tmp_path) -> None:
    reg, anims = setup(tmp_path, [record("HELLO", asset_id="hello", **FULL)], {"hello": valid_clip("HELLO")})
    app.dependency_overrides[get_settings] = lambda: Settings(sign_registry=reg, animation_dir=anims)
    body = client.get("/api/avatar/registry").json()
    assert body["totals"]["clip_unreviewed"] == 1 and body["signs"][0]["status"] == "clip_unreviewed"
    app.dependency_overrides[get_settings] = lambda: Settings(sign_registry=tmp_path / "nope.json")
    assert client.get("/api/avatar/registry").status_code == 503
