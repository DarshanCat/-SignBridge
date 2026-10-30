"""Build the video index CSV (video,label,signer_id[,split]) for preprocess_videos from a folder tree. Run from backend/:

    python -m training.make_manifest --root <dir> --out <index.csv> [--label-level 1] [--signer-regex "(S\\d+)"]
                                     [--split-file splits.csv] [--hash-duplicates]

Label = name of the directory `--label-level` levels above the file (1 = parent). Signer = first regex group matched on the
relative path; without --signer-regex every signer is "unknown", which blocks signer-independent training. Nothing is
dropped silently: every excluded file is written to <out>.exclusions.csv with its reason.
"""

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path

from training.data import DatasetError

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def build_index(
    root: Path,
    *,
    label_level: int = 1,
    signer_regex: str | None = None,
    split_map: dict[str, str] | None = None,
    hash_duplicates: bool = False,
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Return (rows, exclusions) where exclusions are (relative path, reason)."""
    if not root.is_dir():
        raise DatasetError(f"Not a directory: {root}")
    pattern = re.compile(signer_regex) if signer_regex else None
    rows: list[dict] = []
    excluded: list[tuple[str, str]] = []
    seen: dict[str, str] = {}

    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS):
        rel = path.relative_to(root)
        rel_s = rel.as_posix()
        if len(rel.parts) <= label_level:
            excluded.append((rel_s, f"no directory {label_level} level(s) above the file to use as a label"))
            continue
        label = rel.parts[-1 - label_level].strip()
        signer = "unknown"
        if pattern:
            m = pattern.search(rel_s)
            if not m or not m.groups():
                excluded.append((rel_s, "signer regex did not match"))
                continue
            signer = m.group(1)
        split = ""
        if split_map is not None:
            if rel_s not in split_map:
                excluded.append((rel_s, "not listed in the split file"))
                continue
            split = split_map[rel_s]
        if hash_duplicates:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in seen:
                excluded.append((rel_s, f"byte-identical duplicate of {seen[digest]}"))
                continue
            seen[digest] = rel_s
        row = {"video": rel_s, "label": label, "signer_id": signer}
        if split_map is not None:
            row["split"] = split
        rows.append(row)
    return rows, excluded


def read_split_file(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not {"video", "split"} <= set(reader.fieldnames or []):
            raise DatasetError("split file needs columns video,split")
        out = {r["video"].replace("\\", "/"): r["split"].strip() for r in reader}
    bad = {v for v in out.values() if v not in {"train", "val", "test"}}
    if bad:
        raise DatasetError(f"split file has invalid split names: {sorted(bad)}")
    return out


def write_outputs(rows: list[dict], excluded: list[tuple[str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["video", "label", "signer_id"] + (["split"] if rows and "split" in rows[0] else [])
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with out.with_suffix(".exclusions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["video", "reason"])
        w.writerows(excluded)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--label-level", type=int, default=1)
    p.add_argument("--signer-regex")
    p.add_argument("--split-file", type=Path)
    p.add_argument("--hash-duplicates", action="store_true")
    a = p.parse_args()
    try:
        split_map = read_split_file(a.split_file) if a.split_file else None
        rows, excluded = build_index(
            a.root, label_level=a.label_level, signer_regex=a.signer_regex, split_map=split_map,
            hash_duplicates=a.hash_duplicates,
        )
    except (DatasetError, re.error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    write_outputs(rows, excluded, a.out)
    print(f"Indexed {len(rows)} video(s), excluded {len(excluded)} (see {a.out.with_suffix('.exclusions.csv')})")
    if rows and not a.signer_regex:
        print("WARNING: signer_id is 'unknown' for every row; signer-independent splitting is impossible.", file=sys.stderr)
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
