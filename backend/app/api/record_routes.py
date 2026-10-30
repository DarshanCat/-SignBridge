"""Sign recorder: accept a landmark take (no video), check its quality, store it and return an unreviewed retargeted clip."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.avatar.clip import ClipFile
from app.core.config import Settings, get_settings
from app.recording import RecordingError, check_take, clean_gloss, frames_to_features, save_take, take_to_clip
from app.schemas.landmarks import MAX_FRAMES, LandmarkFrame

logger = logging.getLogger("signbridge")
router = APIRouter()


class RecordRequest(BaseModel):
    gloss: str = Field(min_length=1, max_length=40)
    fps: float = Field(gt=0, description="frame rate measured in the browser: frames captured divided by seconds")
    frames: list[LandmarkFrame] = Field(min_length=1, max_length=MAX_FRAMES)


class RecordResponse(BaseModel):
    accepted: bool
    gloss: str
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
    except RecordingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    features, pose_ok = frames_to_features(req.frames)
    quality = check_take(features, pose_ok, req.fps)
    if not quality.accepted:
        return RecordResponse(accepted=False, gloss=gloss, reasons=quality.reasons, stats=quality.stats.__dict__, saved=False)
    try:
        npy, stamp = save_take(settings.record_dir, gloss, features, quality.stats)
        clip = take_to_clip(features, gloss, quality.stats, npy.name)
        ClipFile.model_validate(clip)
        clip_path = npy.with_name(f"{stamp}.clip.json")
        clip_path.write_text(json.dumps(clip), encoding="utf-8")
    except (RecordingError, ValueError) as exc:
        logger.warning("recording rejected after quality check: %s", exc)
        return RecordResponse(accepted=False, gloss=gloss, reasons=[f"Could not build a clip from this take: {exc}"], stats=quality.stats.__dict__, saved=True,
                              feature_file=None)
    return RecordResponse(
        accepted=True, gloss=gloss, reasons=[], stats=quality.stats.__dict__, saved=True,
        feature_file=f"{gloss}/{npy.name}", clip_file=f"{gloss}/{clip_path.name}", clip=clip,
    )
