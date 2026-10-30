"""Convert labelled ISL videos to landmark features. Run from backend/:

    python -m training.preprocess_videos --index ..\\data\\raw\\<dataset>\\index.csv --out ..\\data\\processed\\<dataset>

Videos are read locally and only landmark arrays are written. Create dataset_info.json in --out afterwards
(or copy it there) before validating; see docs/DATASET_GUIDE.md.
"""

import argparse
import sys
from pathlib import Path

from training.data import DatasetError
from training.video_features import process_videos


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True, help="CSV with columns video,label,signer_id")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--stride", type=int, default=1, help="process every Nth frame")
    a = p.parse_args()
    try:
        written, skipped = process_videos(a.index, a.out, a.stride)
    except DatasetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {written} feature file(s) to {a.out}")
    for msg in skipped:
        print(f"SKIPPED: {msg}", file=sys.stderr)
    return 0 if written else 2


if __name__ == "__main__":
    raise SystemExit(main())
