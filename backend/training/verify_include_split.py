"""Cross-check the authors' split lists against what the streaming run actually processed. Run from backend/:

    python -m training.verify_include_split --raw ..\\data\\raw\\include --out ..\\data\\processed\\include [--report <json>]

Reports, per split: listed videos, processed and usable, excluded (with reasons), and listed videos never seen in any zip.
Also checks that no video appears in two splits and that every manifest row maps back to a listed video.
Exits 2 if anything is missing or inconsistent, so it can gate training.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from training.include_stream import SPLIT_FILES, VIDEO_RE


def verify(raw: Path, out: Path, expected_zips: int | None = None) -> dict:
    listed: dict[str, tuple[str, str]] = {}  # lower path -> (split, original path)
    duplicates_across_splits: list[str] = []
    for split, name in SPLIT_FILES.items():
        for line in (raw / "splits" / name).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if VIDEO_RE.search(line):
                key = line.lower()
                if key in listed and listed[key][0] != split:
                    duplicates_across_splits.append(line)
                listed[key] = (split, line)

    seen: dict[str, dict] = {}
    parts = sorted((out / "_parts").glob("*.csv"))
    for p in parts:
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                seen[r["member"].lower()] = r

    per_split = {s: Counter() for s in SPLIT_FILES}
    for key, (split, _) in listed.items():
        per_split[split]["listed"] += 1
        r = seen.get(key)
        if r is None:
            per_split[split]["never_seen"] += 1
        elif r["npy"]:
            per_split[split]["usable"] += 1
        else:
            per_split[split]["excluded"] += 1
    unlisted_processed = sorted(k for k in seen if k not in listed)
    split_mismatch = sorted(k for k, r in seen.items() if k in listed and listed[k][0] != r["split"])

    manifest_rows = 0
    manifest_ok = True
    if (out / "manifest.csv").exists():
        with (out / "manifest.csv").open(newline="", encoding="utf-8") as f:
            manifest_rows = sum(1 for _ in csv.DictReader(f))
        usable = sum(c["usable"] for c in per_split.values())
        manifest_ok = manifest_rows == usable

    problems = []
    if expected_zips is not None and len(parts) != expected_zips:
        problems.append(f"{len(parts)} of {expected_zips} zip parts finished")
    for s, c in per_split.items():
        if c["never_seen"]:
            problems.append(f"{c['never_seen']} listed {s} video(s) were not found in any processed zip")
    if duplicates_across_splits:
        problems.append(f"{len(duplicates_across_splits)} video(s) listed in more than one split")
    if split_mismatch:
        problems.append(f"{len(split_mismatch)} processed video(s) carry a different split than the lists")
    if not manifest_ok:
        problems.append("manifest row count differs from the number of usable videos")
    return {
        "zip_parts_finished": len(parts),
        "per_split": {s: dict(c) for s, c in per_split.items()},
        "processed_but_not_in_lists": len(unlisted_processed),
        "processed_but_not_in_lists_examples": unlisted_processed[:5],
        "videos_in_two_splits": duplicates_across_splits[:5],
        "manifest_rows": manifest_rows,
        "signer_ids_available": False,
        "signer_independence": "UNVERIFIED: the dataset publishes no signer IDs; the split is the authors' predefined list",
        "problems": problems,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--expected-zips", type=int, default=44)
    p.add_argument("--report", type=Path)
    a = p.parse_args()
    report = verify(a.raw, a.out, a.expected_zips)
    text = json.dumps(report, indent=2)
    print(text)
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(text, encoding="utf-8")
    return 2 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
