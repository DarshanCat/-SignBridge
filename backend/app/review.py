"""Signer review records: the only place in the code that writes a review, and it is called only by the Signer review page's endpoint.

A review is a signer's rating of one avatar clip: clarity 1 to 5, correct or wrong, an optional comment, the reviewer's ID. Records are appended to
<review_dir>/<REVIEWER>.jsonl (landmarks and clips are never touched; nothing is overwritten, a second review of the same sign is a new line and the
latest one counts). Nothing in the code decides, infers or sets that a sign is reviewed or verified: no clip file, no registry entry and no label
changes because of a review. The records are data for people to read; the clip files stay "not signer reviewed" until a person decides otherwise.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REVIEWER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
GLOSS_RE = re.compile(r"^[A-Z0-9][A-Z0-9:-]{0,39}$")
VERDICTS = ("correct", "wrong")
MAX_COMMENT = 500
SOURCE = "signer-review-page"


class ReviewError(ValueError):
    pass


def clean_reviewer(raw: str) -> str:
    rid = raw.strip()
    if not REVIEWER_RE.match(rid):
        raise ReviewError("Reviewer ID must be 1 to 32 characters: letters, digits, hyphen or underscore, starting with a letter or digit (for example R01, not a name).")
    return rid.upper()


def clip_hash(animation_dir: Path, gloss: str) -> str | None:
    """sha256 of the clip file reviewed, so a review stays tied to that version of the clip (None if the file is not there)."""
    p = animation_dir / f"{gloss.lower()}.json"
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def validate(gloss: str, clarity: int, verdict: str, comment: str, known_glosses: set[str]) -> tuple[str, str]:
    g = gloss.strip().upper()
    if not GLOSS_RE.match(g) or g not in known_glosses:
        raise ReviewError("That sign has no animation clip, so there is nothing to review.")
    if isinstance(clarity, bool) or not isinstance(clarity, int) or not 1 <= clarity <= 5:
        raise ReviewError("Clarity is a whole number from 1 to 5.")
    if verdict not in VERDICTS:
        raise ReviewError("Mark the sign as correct or wrong.")
    c = comment.strip()
    if len(c) > MAX_COMMENT:
        raise ReviewError(f"A comment is at most {MAX_COMMENT} characters.")
    return g, c


def append_review(
    review_dir: Path, reviewer: str, gloss: str, clarity: int, verdict: str, comment: str, animation_dir: Path, known_glosses: set[str],
    now: datetime | None = None,
) -> dict:
    """Validate and append one review line. Returns the stored record."""
    rid = clean_reviewer(reviewer)
    g, c = validate(gloss, clarity, verdict, comment, known_glosses)
    now = now or datetime.now(timezone.utc)
    record = {
        "reviewer_id": rid, "gloss": g, "clarity": clarity, "verdict": verdict, "comment": c, "reviewed_at_utc": now.isoformat(),
        "clip_sha256": clip_hash(animation_dir, g), "source": SOURCE,
    }
    review_dir.mkdir(parents=True, exist_ok=True)
    with (review_dir / f"{rid}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_reviews(review_dir: Path, reviewer: str) -> list[dict]:
    """All records of one reviewer, oldest first. A line that cannot be read is skipped, never fixed."""
    rid = clean_reviewer(reviewer)
    path = review_dir / f"{rid}.jsonl"
    out: list[dict] = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("reviewer_id") == rid and "gloss" in rec:
            out.append(rec)
    return out


def latest_by_gloss(records: list[dict]) -> dict[str, dict]:
    """The newest review of each sign (the file is in time order)."""
    return {r["gloss"]: r for r in records}
