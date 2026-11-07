"""Signer review: records are appended by the review endpoint only, validated, tied to the clip version, and change nothing else."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app
from app.review import ReviewError, clean_reviewer, latest_by_gloss, validate
from tests.helpers import valid_clip

client = TestClient(app)
APP_DIR = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture()
def env(tmp_path: Path):
    anims = tmp_path / "anims"
    anims.mkdir()
    for g in ("HELLO", "DOCTOR"):
        (anims / f"{g.lower()}.json").write_text(json.dumps(valid_clip(g)), encoding="utf-8")
    settings = Settings(review_dir=tmp_path / "reviews", animation_dir=anims, recording_enabled=True)
    app.dependency_overrides[get_settings] = lambda: settings
    yield tmp_path
    app.dependency_overrides.clear()


def body(**kw):
    return {"reviewer_id": "r01", "gloss": "hello", "clarity": 4, "verdict": "correct", "comment": "clear, slightly fast", **kw}


def test_a_review_is_stored_with_the_reviewer_and_the_clip_version(env: Path) -> None:
    r = client.post("/api/review/submit", json=body())
    assert r.status_code == 200
    rec = r.json()
    assert rec["reviewer_id"] == "R01" and rec["gloss"] == "HELLO" and rec["clarity"] == 4 and rec["verdict"] == "correct"
    clip = (env / "anims" / "hello.json").read_bytes()
    assert rec["clip_sha256"] == hashlib.sha256(clip).hexdigest()
    line = (env / "reviews" / "R01.jsonl").read_text(encoding="utf-8").strip()
    stored = json.loads(line)
    assert stored["source"] == "signer-review-page" and stored["comment"] == "clear, slightly fast" and "reviewed_at_utc" in stored


def test_reviews_are_appended_never_overwritten_and_the_latest_counts(env: Path) -> None:
    client.post("/api/review/submit", json=body(clarity=2, verdict="wrong", comment="hand too low"))
    client.post("/api/review/submit", json=body(clarity=5, verdict="correct", comment="after the fix"))
    client.post("/api/review/submit", json=body(gloss="doctor", clarity=3))
    lines = (env / "reviews" / "R01.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 and json.loads(lines[0])["comment"] == "hand too low"  # the first record is still there
    mine = client.get("/api/review/mine", params={"reviewer_id": "R01"}).json()
    assert mine["total_clips"] == 2 and mine["reviewed"] == 2
    by = {r["gloss"]: r for r in mine["reviews"]}
    assert by["HELLO"]["clarity"] == 5 and by["HELLO"]["comment"] == "after the fix"
    other = client.get("/api/review/mine", params={"reviewer_id": "R02"}).json()
    assert other["reviewed"] == 0 and other["reviews"] == []  # reviewers do not see each other's records


@pytest.mark.parametrize("change,status", [
    ({"clarity": 0}, 422), ({"clarity": 6}, 422), ({"clarity": 2.5}, 422), ({"verdict": "maybe"}, 422), ({"gloss": "nosuchsign"}, 422),
    ({"comment": "x" * 501}, 422), ({"reviewer_id": "Ravi Kumar"}, 422), ({"reviewer_id": "../x"}, 422), ({"gloss": "../hello"}, 422),
])
def test_bad_reviews_are_refused_and_write_nothing(env: Path, change: dict, status: int) -> None:
    assert client.post("/api/review/submit", json=body(**change)).status_code == status
    assert not (env / "reviews").exists()


def test_a_review_changes_no_clip_registry_or_flag(env: Path) -> None:
    registry = Path(__file__).resolve().parents[1] / "config" / "sign_registry.json"
    before = (hashlib.sha256(registry.read_bytes()).hexdigest(), {p.name: p.read_bytes() for p in (env / "anims").iterdir()})
    client.post("/api/review/submit", json=body())
    after = (hashlib.sha256(registry.read_bytes()).hexdigest(), {p.name: p.read_bytes() for p in (env / "anims").iterdir()})
    assert before == after
    assert "review_status" not in (env / "anims" / "hello.json").read_text(encoding="utf-8")


def test_the_endpoints_are_off_when_recording_is_disabled(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(review_dir=tmp_path / "reviews", recording_enabled=False)
    try:
        assert client.post("/api/review/submit", json=body()).status_code == 403
        assert client.get("/api/review/mine", params={"reviewer_id": "R01"}).status_code == 403
        assert not (tmp_path / "reviews").exists()
    finally:
        app.dependency_overrides.clear()


def test_validation_helpers() -> None:
    assert clean_reviewer(" r-01 ") == "R-01"
    with pytest.raises(ReviewError):
        clean_reviewer("")
    assert validate(" hello ", 3, "wrong", "  ok  ", {"HELLO"}) == ("HELLO", "ok")
    with pytest.raises(ReviewError):
        validate("hello", True, "correct", "", {"HELLO"})  # a boolean is not a rating
    assert latest_by_gloss([{"gloss": "A", "n": 1}, {"gloss": "B", "n": 2}, {"gloss": "A", "n": 3}]) == {"A": {"gloss": "A", "n": 3}, "B": {"gloss": "B", "n": 2}}


def test_only_the_review_endpoint_writes_reviews() -> None:
    """Static guard for the rule that code never sets a review flag: the writer is referenced by the review route and nowhere else."""
    users = sorted(str(p.relative_to(APP_DIR)).replace("\\", "/") for p in APP_DIR.rglob("*.py")
                   if "append_review" in p.read_text(encoding="utf-8") or "review_dir" in p.read_text(encoding="utf-8"))
    assert users == ["api/review_routes.py", "core/config.py", "review.py"]
    # and no code assigns a reviewed flag: neither the clip's review_status nor the registry's signer_reviewed is ever set to the reviewed value in the app code
    import re

    pattern = re.compile(r"signer_reviewed\s*=\s*True|review_status\s*=\s*[\"']signer_reviewed|\[[\"']review_status[\"']\]\s*=|\[[\"']signer_reviewed[\"']\]\s*=")
    offenders = [f"{p.relative_to(APP_DIR)}:{n}" for p in APP_DIR.rglob("*.py") for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if pattern.search(line)]
    assert offenders == []
