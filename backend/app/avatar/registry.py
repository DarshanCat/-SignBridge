from pathlib import Path

from app.avatar.clip import ClipError, load_clip
from app.schemas.status import AnimationInfo, AnimationRegistryResponse


INDEX_FILE = "index.json"  # gloss to clip index written next to the clips; not a clip itself


_cache: dict[Path, tuple[tuple, AnimationRegistryResponse]] = {}


def _signature(files: list[Path]) -> tuple:
    out = []
    for p in files:
        st = p.stat()
        out.append((p.name, st.st_mtime_ns, st.st_size))
    return tuple(out)


def list_animations(animation_dir: Path) -> AnimationRegistryResponse:
    """List valid sign clips (*.json) found on disk, one per gloss token. Invalid files are reported, not served.

    The result is cached per folder and recomputed whenever a clip file is added, removed or changed (name, mtime and size are compared),
    so each request no longer re-reads and re-validates every clip.
    """
    files = sorted(p for p in animation_dir.glob("*.json") if p.name != INDEX_FILE) if animation_dir.is_dir() else []
    sig = _signature(files)
    hit = _cache.get(animation_dir)
    if hit and hit[0] == sig:
        return hit[1]
    result = _list_animations_uncached(files)
    _cache[animation_dir] = (sig, result)
    return result


def _list_animations_uncached(files: list[Path]) -> AnimationRegistryResponse:
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
