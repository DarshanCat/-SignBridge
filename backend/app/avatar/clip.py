"""Sign animation clip file format (JSON), one file per gloss: frontend/public/animations/<gloss>.json.

Rotations are Euler XYZ radians relative to the rest pose (arms hanging down, palms toward the body).
A negative x rotation on an arm bone raises it forward. Clips should start and end at the rest pose.
Every clip must state its source and license so provenance can be checked.
"""

import json
import math
from pathlib import Path

from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

BONES: list[str] = [
    "spine", "chest", "neck", "head",
    "upperArm_l", "foreArm_l", "hand_l", "hand_l.thumb", "hand_l.index", "hand_l.middle", "hand_l.ring", "hand_l.pinky",
    "upperArm_r", "foreArm_r", "hand_r", "hand_r.thumb", "hand_r.index", "hand_r.middle", "hand_r.ring", "hand_r.pinky",
]
MAX_DURATION = 20.0


class Keyframe(BaseModel):
    t: float = Field(ge=0)
    rot: list[float] = Field(min_length=3, max_length=3)

    @field_validator("rot")
    @classmethod
    def _finite(cls, v: list[float]) -> list[float]:
        if not all(math.isfinite(x) for x in v):
            raise ValueError("rotation values must be finite")
        return v


class Track(BaseModel):
    bone: str
    keyframes: list[Keyframe] = Field(min_length=1)

    @field_validator("bone")
    @classmethod
    def _known_bone(cls, v: str) -> str:
        if v not in BONES:
            raise ValueError(f"unknown bone {v!r}")
        return v

    @model_validator(mode="after")
    def _sorted(self) -> "Track":
        times = [k.t for k in self.keyframes]
        if times != sorted(times):
            raise ValueError(f"keyframes for {self.bone} must be in time order")
        return self


class ClipSource(BaseModel):
    author: str = Field(min_length=1)
    license: str = Field(min_length=1)
    description: str = Field(min_length=1)
    # Every clip is not signer reviewed until an ISL signer has checked it; the sign registry decides what counts as verified.
    review_status: Literal["not_signer_reviewed", "signer_reviewed"] = "not_signer_reviewed"
    # For clips retargeted from a dataset sample: which sample was used and why (video file name, feature file, missing-hand counts).
    source_sample: dict | None = None
    # Where the landmarks came from: a retarget of a dataset sample, or a take the user recorded with the recorder tool.
    origin: Literal["include-retarget", "self-recorded"] | None = None


class ClipFile(BaseModel):
    gloss: str = Field(min_length=1)
    duration: float = Field(gt=0, le=MAX_DURATION)
    tracks: list[Track] = Field(min_length=1)
    source: ClipSource

    @model_validator(mode="after")
    def _within_duration(self) -> "ClipFile":
        for tr in self.tracks:
            if tr.keyframes[-1].t > self.duration:
                raise ValueError(f"track {tr.bone} extends past the clip duration")
        return self


class ClipError(Exception):
    pass


def load_clip(path: Path) -> ClipFile:
    try:
        clip = ClipFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ClipError(f"{path.name}: {exc}") from exc
    if clip.gloss.strip().upper() != path.stem.upper():
        raise ClipError(f"{path.name}: gloss {clip.gloss!r} does not match the file name")
    return clip
