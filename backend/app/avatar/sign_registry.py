"""Per-sign provenance registry (backend/config/sign_registry.json) checked against the clips on disk."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.avatar.clip import ClipError, load_clip

Status = Literal["no_clip", "clip_unreviewed", "verified", "missing_asset"]


class SignRecord(BaseModel):
    gloss: str
    meaning: str
    context: str
    reference_source: str | None = None
    asset_id: str | None = None  # clip file stem, e.g. "hello" for hello.json
    license: str | None = None
    attribution: str | None = None
    verification_status: str = "no_clip"  # what the registry claims; the computed status below is what is trusted
    visually_reviewed: bool = False
    signer_reviewed: bool = False


class SignRegistryFile(BaseModel):
    signs: list[SignRecord]


class SignStatus(BaseModel):
    gloss: str
    meaning: str
    status: Status
    asset_id: str | None
    license: str | None
    visually_reviewed: bool
    signer_reviewed: bool
    problems: list[str]


class RegistryReport(BaseModel):
    signs: list[SignStatus]
    unregistered_clips: list[str]
    totals: dict[str, int]


class RegistryError(Exception):
    pass


def load_registry(path: Path) -> SignRegistryFile:
    try:
        reg = SignRegistryFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise RegistryError(f"Could not load sign registry {path}: {exc}") from exc
    glosses = [s.gloss.strip().upper() for s in reg.signs]
    if len(set(glosses)) != len(glosses):
        raise RegistryError("Sign registry has duplicate glosses")
    return reg


def build_report(registry_path: Path, animation_dir: Path) -> RegistryReport:
    """Compute each sign's real status from the files. A sign is `verified` only with a valid clip AND both review flags."""
    reg = load_registry(registry_path)
    clips: dict[str, Path] = {}
    if animation_dir.is_dir():
        for p in sorted(animation_dir.glob("*.json")):
            clips[p.stem.lower()] = p

    statuses: list[SignStatus] = []
    used: set[str] = set()
    for s in reg.signs:
        gloss = s.gloss.strip().upper()
        problems: list[str] = []
        status: Status = "no_clip"
        if s.asset_id:
            path = clips.get(s.asset_id.lower())
            used.add(s.asset_id.lower())
            if path is None:
                status, problems = "missing_asset", [f"registry names asset {s.asset_id!r} but the file is not present"]
            else:
                try:
                    clip = load_clip(path)
                    if clip.gloss.strip().upper() != gloss:
                        problems.append(f"clip gloss {clip.gloss!r} differs from registry gloss {gloss!r}")
                    if not (s.license and s.attribution and s.reference_source):
                        problems.append("license, attribution and reference_source must all be recorded")
                    status = "clip_unreviewed"
                    if s.visually_reviewed and s.signer_reviewed and not problems:
                        status = "verified"
                except ClipError as exc:
                    status, problems = "missing_asset", [f"asset is invalid: {exc}"]
        if s.verification_status == "verified" and status != "verified":
            problems.append("registry claims verified but the evidence on disk does not support it")
        statuses.append(SignStatus(
            gloss=gloss, meaning=s.meaning, status=status, asset_id=s.asset_id, license=s.license,
            visually_reviewed=s.visually_reviewed, signer_reviewed=s.signer_reviewed, problems=problems,
        ))
    totals = {k: sum(x.status == k for x in statuses) for k in ("no_clip", "clip_unreviewed", "verified", "missing_asset")}
    totals["signs"] = len(statuses)
    return RegistryReport(signs=statuses, unregistered_clips=sorted(set(clips) - used), totals=totals)
