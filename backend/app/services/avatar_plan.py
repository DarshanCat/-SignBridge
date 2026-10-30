from pathlib import Path

from app.avatar.registry import list_animations
from app.schemas.translation import AvatarPlanResponse, PlanStep
from app.translation.labels import normalize_gloss


def plan_animations(gloss: list[str], animation_dir: Path) -> AvatarPlanResponse:
    """Map each gloss token to a real animation clip on disk, or mark it as missing."""
    clips = {a.gloss: a.clip_url for a in list_animations(animation_dir).animations}
    steps = [PlanStep(gloss=g, available=g in clips, clip_url=clips.get(g)) for g in normalize_gloss(gloss)]
    missing = [s.gloss for s in steps if not s.available]
    playable = bool(steps) and not missing
    if playable:
        message = f"All {len(steps)} sign(s) have animation clips."
    elif len(missing) == len(steps):
        message = "No animation clips are available for these signs, so nothing can be played."
    else:
        message = f"{len(missing)} of {len(steps)} sign(s) have no animation clip: {', '.join(missing)}."
    return AvatarPlanResponse(steps=steps, missing=missing, playable=playable, message=message)
