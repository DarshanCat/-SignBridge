"""Dataset quality audit for the processed INCLUDE features. Read-only on data; writes reports. Run from backend/:

    python -m training.audit_include --raw ..\\data\\raw\\include --out ..\\data\\processed\\include --reports ..\\docs\\evaluation

Writes dataset_quality.json, class_distribution.csv, split_integrity.json (and returns the numbers used by the Markdown report).
It never modifies the manifest, the feature files or the raw split lists.
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.recognition.landmarks import FEATURE_DIM, HAND_POINTS, POSE_POINTS
from training.include_stream import SPLIT_FILES, VIDEO_RE

EXPECTED_SPLIT_COUNTS = {"train": 3127, "val": 348, "test": 817}
POSE_END = POSE_POINTS * 3
LEFT_END = POSE_END + HAND_POINTS * 3


def read_lists(raw: Path) -> dict[str, dict[str, str]]:
    lists: dict[str, dict[str, str]] = {}
    for split, name in SPLIT_FILES.items():
        d: dict[str, str] = {}
        for line in (raw / "splits" / name).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if VIDEO_RE.search(line):
                d[line.lower()] = line
        lists[split] = d
    return lists


def audit(raw: Path, out: Path) -> tuple[dict, dict, list[dict]]:
    # parts records: member -> row (usable or excluded)
    seen: dict[str, dict] = {}
    parts = sorted((out / "_parts").glob("*.csv"))
    for p in parts:
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                seen[r["member"].lower()] = r
    npy_to_member = {r["npy"]: m for m, r in seen.items() if r["npy"]}

    manifest = list(csv.DictReader((out / "manifest.csv").open(newline="", encoding="utf-8")))
    problems: dict[str, list] = defaultdict(list)
    shapes, dtypes, lengths = Counter(), Counter(), []
    hashes: dict[str, list[str]] = defaultdict(list)
    path_counts = Counter(r["path"] for r in manifest)
    per_class = defaultdict(lambda: {"n": 0, "frames": 0, "no_left": 0, "no_right": 0, "no_hands": 0, "lengths": [], "splits": Counter()})
    nonfinite = 0
    for r in manifest:
        fp = out / r["path"]
        if not fp.is_file():
            problems["missing_file"].append(r["path"])
            continue
        try:
            a = np.load(fp)
        except Exception as exc:  # noqa: BLE001 - corrupted arrays are reported, never skipped silently
            problems["unreadable"].append(f"{r['path']}: {exc}")
            continue
        shapes[str(a.shape[1:]) if a.ndim == 2 else f"ndim={a.ndim}"] += 1
        dtypes[str(a.dtype)] += 1
        if a.ndim != 2 or a.shape[1] != FEATURE_DIM:
            problems["bad_shape"].append(f"{r['path']}: {a.shape}")
            continue
        if a.shape[0] == 0:
            problems["empty"].append(r["path"])
            continue
        if not np.isfinite(a).all():
            nonfinite += 1
            problems["non_finite"].append(r["path"])
            continue
        hashes[hashlib.sha256(a.tobytes()).hexdigest()].append(r["path"])
        left_missing = ~a[:, POSE_END:LEFT_END].any(axis=1)
        right_missing = ~a[:, LEFT_END:].any(axis=1)
        c = per_class[r["label"]]
        c["n"] += 1
        c["frames"] += a.shape[0]
        c["no_left"] += int(left_missing.sum())
        c["no_right"] += int(right_missing.sum())
        c["no_hands"] += int((left_missing & right_missing).sum())
        c["lengths"].append(int(a.shape[0]))
        c["splits"][r["split"]] += 1
        lengths.append(int(a.shape[0]))

    duplicate_paths = [p for p, n in path_counts.items() if n > 1]
    duplicate_content = [v for v in hashes.values() if len(v) > 1]
    orphans = sorted(set(f.name for f in out.glob("*.npy")) - set(r["path"] for r in manifest))
    unknown_manifest = [r["path"] for r in manifest if r["path"] not in npy_to_member]

    # split integrity against the authors' lists
    lists = read_lists(raw)
    listed_all: dict[str, tuple[str, str]] = {}
    in_two = []
    for split, d in lists.items():
        for k, orig in d.items():
            if k in listed_all and listed_all[k][0] != split:
                in_two.append(orig)
            listed_all[k] = (split, orig)
    manifest_split = Counter(r["split"] for r in manifest)
    per_split = {}
    missing_listed: dict[str, list[str]] = {s: [] for s in lists}
    for split, d in lists.items():
        usable = sum(1 for k in d if k in seen and seen[k]["npy"])
        excluded = sum(1 for k in d if k in seen and not seen[k]["npy"])
        never = [orig for k, orig in d.items() if k not in seen]
        missing_listed[split] = never
        per_split[split] = {
            "expected_by_task": EXPECTED_SPLIT_COUNTS[split],
            "listed": len(d),
            "usable_processed": usable,
            "excluded_with_reason": excluded,
            "never_seen_in_any_zip": len(never),
            "manifest_rows": manifest_split.get(split, 0),
        }
    processed_not_listed = sorted(k for k in seen if k not in listed_all)
    wrong_split = sorted(k for k, r in seen.items() if k in listed_all and listed_all[k][0] != r["split"])
    manifest_not_listed = [r["path"] for r in manifest if npy_to_member.get(r["path"], "").lower() not in listed_all]
    split_labels = {s: {r["label"] for r in manifest if r["split"] == s} for s in lists}
    all_labels = {r["label"] for r in manifest}

    # duplicate content across splits (possible leakage)
    path_split = {r["path"]: r["split"] for r in manifest}
    leak = [v for v in duplicate_content if len({path_split[p] for p in v}) > 1]

    missing_by_category = Counter(o.split("/")[0] for lst in missing_listed.values() for o in lst)
    missing_by_label = Counter("/".join(o.split("/")[:2]) for lst in missing_listed.values() for o in lst)

    all_len = np.array(lengths) if lengths else np.array([0])
    n_frames = int(sum(c["frames"] for c in per_class.values()))
    stats = {
        "total_usable_samples": len(manifest),
        "classes": len(per_class),
        "samples_per_split": dict(manifest_split),
        "feature_dim": FEATURE_DIM,
        "feature_layout": "pose 33x3 | left hand 21x3 | right hand 21x3 (x, y, z), shoulder-midpoint origin, shoulder-width scale; face not used",
        "dtype_counts": dict(dtypes),
        "trailing_shape_counts": dict(shapes),
        "sequence_length_frames": {
            "min": int(all_len.min()), "p5": int(np.percentile(all_len, 5)), "median": int(np.median(all_len)),
            "mean": round(float(all_len.mean()), 2), "p95": int(np.percentile(all_len, 95)), "max": int(all_len.max()),
        },
        "frames_total": n_frames,
        "missing_landmark_rates": {
            "frame_without_left_hand": round(sum(c["no_left"] for c in per_class.values()) / max(1, n_frames), 4),
            "frame_without_right_hand": round(sum(c["no_right"] for c in per_class.values()) / max(1, n_frames), 4),
            "frame_without_any_hand": round(sum(c["no_hands"] for c in per_class.values()) / max(1, n_frames), 4),
            "frame_without_pose": 0.0,
            "note": "frames without a body pose are discarded during extraction, so every stored frame has a pose; a missing hand is an all-zero block",
        },
        "samples_per_class": {"min": min((c["n"] for c in per_class.values()), default=0), "max": max((c["n"] for c in per_class.values()), default=0),
                              "median": float(np.median([c["n"] for c in per_class.values()])) if per_class else 0},
        "exclusions": {"count": sum(1 for r in seen.values() if not r["npy"]), "reasons": Counter(r["message"] for r in seen.values() if not r["npy"]).most_common(10)},
        "non_finite_arrays": nonfinite,
    }
    integrity = {
        "zip_part_records": len(parts),
        "manifest_rows": len(manifest),
        "feature_files_on_disk": len(list(out.glob("*.npy"))),
        "problems": {k: v[:10] for k, v in problems.items()},
        "problem_counts": {k: len(v) for k, v in problems.items()},
        "duplicate_manifest_paths": len(duplicate_paths),
        "duplicate_content_groups": len(duplicate_content),
        "duplicate_content_examples": duplicate_content[:3],
        "feature_files_not_in_manifest": len(orphans),
        "manifest_rows_without_a_part_record": len(unknown_manifest),
    }
    split_report = {
        "labelling": "authors' predefined split (AI4Bharat/INCLUDE train_test_paths); signer independence UNVERIFIED, no signer IDs exist",
        "per_split": per_split,
        "listed_total": sum(len(d) for d in lists.values()),
        "expected_total_by_task": sum(EXPECTED_SPLIT_COUNTS.values()),
        "listed_matches_task_expectation": {s: len(lists[s]) == EXPECTED_SPLIT_COUNTS[s] for s in lists},
        "videos_listed_in_more_than_one_split": in_two[:10],
        "processed_videos_not_in_lists": len(processed_not_listed),
        "processed_videos_not_in_lists_examples": processed_not_listed[:5],
        "manifest_rows_not_in_lists": len(manifest_not_listed),
        "processed_with_split_different_from_lists": len(wrong_split),
        "identical_features_across_splits": len(leak),
        "classes_missing_from_a_split": {s: len(all_labels - split_labels[s]) for s in lists},
        "listed_but_never_seen_by_category": dict(missing_by_category.most_common()),
        "listed_but_never_seen_by_class_top10": dict(missing_by_label.most_common(10)),
        "listed_but_never_seen_examples": {s: missing_listed[s][:5] for s in lists},
        "signer_ids_available": False,
    }
    class_rows = []
    for label, c in sorted(per_class.items()):
        fr = max(1, c["frames"])
        class_rows.append({
            "label": label, "samples": c["n"], "train": c["splits"].get("train", 0), "val": c["splits"].get("val", 0),
            "test": c["splits"].get("test", 0), "median_frames": int(np.median(c["lengths"])),
            "frame_no_left_hand_rate": round(c["no_left"] / fr, 4), "frame_no_right_hand_rate": round(c["no_right"] / fr, 4),
            "frame_no_hands_rate": round(c["no_hands"] / fr, 4),
        })
    return {"statistics": stats, "integrity": integrity}, split_report, class_rows


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--reports", type=Path, required=True)
    a = p.parse_args()
    quality, split_report, class_rows = audit(a.raw, a.out)
    a.reports.mkdir(parents=True, exist_ok=True)
    (a.reports / "dataset_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    (a.reports / "split_integrity.json").write_text(json.dumps(split_report, indent=2), encoding="utf-8")
    with (a.reports / "class_distribution.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(class_rows[0]))
        w.writeheader()
        w.writerows(class_rows)
    print(json.dumps({"integrity": quality["integrity"]["problem_counts"], "per_split": split_report["per_split"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
