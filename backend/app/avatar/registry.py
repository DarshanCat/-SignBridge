from pathlib import Path

from app.avatar.clip import ClipError, load_clip
from app.schemas.status import AnimationInfo, AnimationRegistryResponse


def list_animations(animation_dir: Path) -> AnimationRegistryResponse:
    """List valid sign clips (*.json) found on disk, one per gloss token. Invalid files are reported, not served."""
    files = sorted(animation_dir.glob("*.json")) if animation_dir.is_dir() else []
    animations: list[AnimationInfo] = []
    invalid: list[str] = []
    for p in files:
        try:
            clip = load_clip(p)
        except ClipError as exc:
            invalid.append(str(exc))
            continue
        animations.append(AnimationInfo(gloss=clip.gloss.strip().upper(), clip_url=f"/animations/{p.name}"))

    if animations:
        message = f"{len(animations)} sign animation clip(s) available."
    else:
        message = "No sign animation clips available yet. English-to-sign playback is disabled."
    if invalid:
        message += f" {len(invalid)} invalid clip file(s) ignored."
    return AnimationRegistryResponse(count=len(animations), animations=animations, message=message, invalid=invalid)
