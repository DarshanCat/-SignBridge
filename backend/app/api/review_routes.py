"""Signer review endpoints (local only, like the recorder: SIGNBRIDGE_RECORDING_ENABLED=false turns them off). The only way a review is written."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.record_routes import require_recording
from app.avatar.registry import list_animations
from app.core.config import Settings, get_settings
from app.review import ReviewError, append_review, clean_reviewer, latest_by_gloss, read_reviews

router = APIRouter(prefix="/api/review", dependencies=[Depends(require_recording)])


class SubmitRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=40)
    gloss: str = Field(min_length=1, max_length=40)
    clarity: int = Field(ge=1, le=5, description="1 = not clear, 5 = very clear")
    verdict: str = Field(description="correct or wrong")
    comment: str = Field(default="", max_length=600)


class ReviewRecord(BaseModel):
    reviewer_id: str
    gloss: str
    clarity: int
    verdict: str
    comment: str
    reviewed_at_utc: str
    clip_sha256: str | None = None


class MineResponse(BaseModel):
    reviewer_id: str
    reviews: list[ReviewRecord]
    total_clips: int
    reviewed: int


def known_glosses(settings: Settings) -> set[str]:
    return {a.gloss for a in list_animations(settings.animation_dir).animations}


@router.post("/submit", response_model=ReviewRecord)
def submit(req: SubmitRequest, settings: Settings = Depends(get_settings)) -> ReviewRecord:
    try:
        rec = append_review(settings.review_dir, req.reviewer_id, req.gloss, req.clarity, req.verdict, req.comment, settings.animation_dir, known_glosses(settings))
    except ReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return ReviewRecord(**{k: rec[k] for k in ReviewRecord.model_fields})


@router.get("/mine", response_model=MineResponse)
def mine(reviewer_id: str, settings: Settings = Depends(get_settings)) -> MineResponse:
    """The newest review of each sign by one reviewer (so the page can show what is done)."""
    try:
        rid = clean_reviewer(reviewer_id)
        latest = latest_by_gloss(read_reviews(settings.review_dir, rid))
    except ReviewError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    total = known_glosses(settings)
    reviews = [ReviewRecord(**{k: r.get(k) for k in ReviewRecord.model_fields}) for g, r in sorted(latest.items()) if g in total]
    return MineResponse(reviewer_id=rid, reviews=reviews, total_clips=len(total), reviewed=len(reviews))
