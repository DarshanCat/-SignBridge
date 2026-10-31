"""Retarget one landmark feature file to a clip. Run from backend/:

    python -m retarget.make_clip --features <sample.npy> --gloss HELLO --out <clip.json> [--fps 30] [--stride 2]

Reads the feature file only. The output is an UNREVIEWED automatic retarget: it is not a verified sign and must not be shipped as one.
The source video frame rate (--fps) is an assumption; INCLUDE does not document it here.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from retarget.clip_builder import build_clip


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--features", type=Path, required=True)
    p.add_argument("--gloss", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fps", type=float, default=30.0)
    p.add_argument("--stride", type=int, default=2)
    p.add_argument("--source-note", default="an INCLUDE sample", help="where the landmarks came from, for the clip provenance")
    a = p.parse_args()
    try:
        seq = np.load(a.features)
        clip = build_clip(
            seq, a.gloss, fps=a.fps, stride=a.stride, author="SignBridge automatic retarget",
            license_text="Derived from INCLUDE (Sridhar et al., ACM MM 2020). Treated as CC BY-NC-SA 4.0: non-commercial only, with attribution, share alike (see DATA_NOTICE.md). The dataset's own licence is unresolved (CC BY 4.0 per Zenodo, CC BY-NC-SA 4.0 per a third party page).",
            description=f"UNREVIEWED automatic retarget of {a.source_note}; fps {a.fps} assumed, stride {a.stride}; not a verified sign",
        )
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(clip), encoding="utf-8")
    print(f"wrote {a.out}: {len(clip['tracks'])} tracks, {clip['duration']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
