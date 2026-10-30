"""Promote a recorded clip into the shipped animations. Run from backend/:

    python -m retarget.promote --clip ..\\data\\recorded\\WATER\\<stamp>.clip.json [--meaning water] [--replace] [--dry-run]

Copies the clip to frontend/public/animations/<gloss>.json, adds it to index.json and the sign registry, and keeps it
`not_signer_reviewed` (registry status `clip_unreviewed`, never verified). It refuses when the gloss already has a clip (a clip file, an
index entry or a registry asset) unless --replace is given. Everything is validated before anything is written.
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.avatar.clip import ClipFile
from app.core.config import BACKEND_DIR, get_settings

INDEX_FILE = "index.json"
SELF_LICENSE = "Self-recorded by the SignBridge user; not redistributed. Not signer reviewed."


class PromoteError(Exception):
    pass


def _read_json(path: Path, default: dict) -> dict:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PromoteError(f"cannot read {path}: {exc}") from None


def promote(clip_path: Path, animation_dir: Path, registry_path: Path, *, replace: bool = False, meaning: str | None = None,
            dry_run: bool = False) -> dict:
    try:
        clip = ClipFile.model_validate(json.loads(clip_path.read_text(encoding="utf-8")))  # full schema validation
    except (OSError, ValueError, ValidationError) as exc:
        raise PromoteError(f"{clip_path.name} is not a valid clip: {exc}") from None
    if clip.source.review_status != "not_signer_reviewed":
        raise PromoteError("only clips marked not_signer_reviewed can be promoted; signer review is recorded by a person, not by this tool")
    gloss = clip.gloss.strip().upper()
    stem = gloss.lower()
    target = animation_dir / f"{stem}.json"

    index_path = animation_dir / INDEX_FILE
    index = _read_json(index_path, {"version": 1, "note": "Automatic retargets; none is signer reviewed or a verified sign.", "clips": {}})
    registry = _read_json(registry_path, {"signs": []})
    if not registry_path.is_file():
        raise PromoteError(f"sign registry not found: {registry_path}")
    signs = registry.get("signs", [])
    record = next((s for s in signs if s.get("gloss", "").upper() == gloss), None)

    existing = []
    if target.exists():
        existing.append(f"clip file {target.name}")
    if gloss in index.get("clips", {}):
        existing.append("an index.json entry")
    if record and record.get("asset_id"):
        existing.append(f"registry asset {record['asset_id']!r}")
    if existing and not replace:
        raise PromoteError(f"{gloss} already has a clip ({', '.join(existing)}); pass --replace to overwrite it")

    raw = json.loads(clip_path.read_text(encoding="utf-8"))
    raw["source"]["review_status"] = "not_signer_reviewed"
    sample = raw["source"].get("source_sample")
    origin = raw["source"].get("origin") or "unknown"
    entry = {"file": target.name, "duration": raw["duration"], "review_status": "not_signer_reviewed", "origin": origin, "source_sample": sample}
    reference = f"{origin} take {sample.get('feature_file', clip_path.name)}" if isinstance(sample, dict) else f"{origin} clip {clip_path.name}"
    fields = {
        "reference_source": reference, "asset_id": stem, "license": raw["source"]["license"] or SELF_LICENSE,
        "attribution": raw["source"]["author"], "verification_status": "clip_unreviewed", "visually_reviewed": False, "signer_reviewed": False,
    }
    if record is None:
        record = {"gloss": gloss, "meaning": meaning or stem.replace("-", " "),
                  "context": f"{origin} clip; sign, context and handshape not reviewed by an ISL signer"}
        signs.append(record)
    elif meaning:
        record["meaning"] = meaning
    record.update(fields)
    registry["signs"] = signs
    index.setdefault("clips", {})[gloss] = entry

    summary = {"gloss": gloss, "clip_file": str(target), "replaced": bool(existing), "dry_run": dry_run, "review_status": "not_signer_reviewed"}
    if dry_run:
        return summary
    animation_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(raw), encoding="utf-8")
    index_path.write_text(json.dumps(index, indent=1), encoding="utf-8")
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> int:
    s = get_settings()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clip", type=Path, required=True)
    ap.add_argument("--animations", type=Path, default=s.animation_dir)
    ap.add_argument("--registry", type=Path, default=s.sign_registry)
    ap.add_argument("--meaning", help="English meaning for a new registry record")
    ap.add_argument("--replace", action="store_true", help="overwrite an existing clip for this gloss")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        r = promote(a.clip, a.animations, a.registry, replace=a.replace, meaning=a.meaning, dry_run=a.dry_run)
    except PromoteError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    print(("Would promote" if r["dry_run"] else "Promoted") + f" {r['gloss']} to {r['clip_file']} (replaced existing: {r['replaced']}); not signer reviewed.")
    if not (BACKEND_DIR / "config" / "gloss_dictionary.json").is_file():
        return 0
    dictionary = json.loads((BACKEND_DIR / "config" / "gloss_dictionary.json").read_text(encoding="utf-8")).get("signs", {})
    if r["gloss"] not in dictionary:
        print(f"Note: {r['gloss']} is not in config/gloss_dictionary.json, so text to gloss will not produce it until it is added there.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
