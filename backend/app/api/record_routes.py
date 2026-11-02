"""Sign recorder: accept a landmark take (no video), check its quality, store it and return an unreviewed retargeted clip."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.avatar.clip import ClipFile
from app.core.config import Settings, get_settings
from app.recording import (
    RecordingError, check_take, clean_gloss, clean_signer, count_takes, frames_to_features, grammar_words, save_take, take_dir, take_to_clip,
)
from nlp.lexicon import load_lexicon
from app.schemas.landmarks import MAX_FRAMES, LandmarkFrame

logger = logging.getLogger("signbridge")


def require_recording(settings: Settings = Depends(get_settings)) -> None:
    """The recorder writes to disk; a public deployment turns it off with SIGNBRIDGE_RECORDING_ENABLED=false."""
    if not settings.recording_enabled:
        raise HTTPException(status_code=403, detail="Recording is disabled on this deployment.")


router = APIRouter(dependencies=[Depends(require_recording)])


class RecordRequest(BaseModel):
    gloss: str = Field(min_length=1, max_length=40)
    fps: float = Field(gt=0, description="frame rate measured in the browser: frames captured divided by seconds")
    frames: list[LandmarkFrame] = Field(min_length=1, max_length=MAX_FRAMES)
    signer_id: str | None = Field(default=None, max_length=40, description="guided sessions: takes go to data/recorded/<signer_id>/<gloss>/")
    make_clip: bool = Field(default=True, description="false in guided sessions (clips can be rebuilt from the features later)")


class RecordResponse(BaseModel):
    accepted: bool
    gloss: str
    signer_id: str | None = None
    reasons: list[str]
    stats: dict
    saved: bool
    feature_file: str | None = None
    clip_file: str | None = None
    clip: dict | None = None
    note: str = (
        "Landmarks only; no video is stored. Takes are kept in the local recordings folder and are not redistributed. "
        "The clip is an automatic retarget and is not signer reviewed."
    )


@router.post("/api/record/sign", response_model=RecordResponse)
def record_sign(req: RecordRequest, settings: Settings = Depends(get_settings)) -> RecordResponse:
    try:
        gloss = clean_gloss(req.gloss)
        signer = clean_signer(req.signer_id) if req.signer_id is not None else None
    except RecordingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    features, pose_ok = frames_to_features(req.frames)
    quality = check_take(features, pose_ok, req.fps)
    if not quality.accepted:
        return RecordResponse(accepted=False, gloss=gloss, signer_id=signer, reasons=quality.reasons, stats=quality.stats.__dict__, saved=False)
    rel = f"{signer}/{gloss}" if signer else gloss
    try:
        npy, stamp = save_take(settings.record_dir, gloss, features, quality.stats, signer_id=signer)
        clip, clip_path = None, None
        if req.make_clip:
            clip = take_to_clip(features, gloss, quality.stats, npy.name, signer)
            ClipFile.model_validate(clip)
            clip_path = npy.with_name(f"{stamp}.clip.json")
            clip_path.write_text(json.dumps(clip), encoding="utf-8")
    except (RecordingError, ValueError) as exc:
        logger.warning("recording rejected after quality check: %s", exc)
        return RecordResponse(accepted=False, gloss=gloss, signer_id=signer, reasons=[f"Could not build a clip from this take: {exc}"], stats=quality.stats.__dict__,
                              saved=True, feature_file=None)
    return RecordResponse(
        accepted=True, gloss=gloss, signer_id=signer, reasons=[], stats=quality.stats.__dict__, saved=True,
        feature_file=f"{rel}/{npy.name}", clip_file=f"{rel}/{clip_path.name}" if clip_path else None, clip=clip,
    )


class RecordPlanResponse(BaseModel):
    glosses: list[str]
    priority: list[str]
    note: str = "Grammar words from the gloss dictionary that are not INCLUDE classes and have no clip; the priority words come first."


@router.get("/api/record/plan", response_model=RecordPlanResponse)
def record_plan(settings: Settings = Depends(get_settings)) -> RecordPlanResponse:
    """The glosses a guided session should record, in order."""
    from app.recording import PRIORITY_GLOSSES

    try:
        lex = load_lexicon(settings.gloss_dictionary)
    except (OSError, ValueError, KeyError):
        raise HTTPException(status_code=503, detail="The gloss dictionary is unavailable or invalid.") from None
    words = grammar_words(lex)
    return RecordPlanResponse(glosses=words, priority=[g for g in PRIORITY_GLOSSES if g in words])


class RecordTakesResponse(BaseModel):
    signer_id: str
    counts: dict[str, int]
    total: int


@router.get("/api/record/takes", response_model=RecordTakesResponse)
def record_takes(signer_id: str, settings: Settings = Depends(get_settings)) -> RecordTakesResponse:
    """Saved takes per gloss for one signer, so a session can resume."""
    try:
        signer = clean_signer(signer_id)
    except RecordingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    counts = count_takes(settings.record_dir, signer)
    return RecordTakesResponse(signer_id=signer, counts=counts, total=sum(counts.values()))
