"""Build a combined training manifest: INCLUDE (authors' split) plus self-recorded takes (signer-level split). Run from backend/:

    python -m training.make_combined_manifest --include-manifest ..\\data\\processed\\include_v2\\manifest.csv --recorded ..\\data\\recorded ^
        --out ..\\data\\processed\\combined_v1 --test-signer P05 --val-signer P04

Rules (see docs/TRAINING_PLAN_SELF_RECORDED.md):
  * INCLUDE rows keep the authors' split and signer_id "unknown"; their files are referenced, never copied or changed.
  * Self-recorded rows get the split of their SIGNER: every take of a test signer is test, of a validation signer is val, all others are train.
    A signer can be in only one split, so the self-recorded test result is on a person the model never saw.
  * Each take is cleaned like the INCLUDE features: frames without a body pose are dropped, then the take is cut to the sign (the same segmenter
    the live recognizer uses, with its rest padding), so training sees what live recognition will classify. Takes without any sign movement are
    left out and listed in the report.
  * Recorded glosses that are INCLUDE classes are labelled with the INCLUDE class name (so they join the class); grammar words keep their gloss.
  * The recorded data and INCLUDE folders are only read. The output folder must not exist yet (nothing is ever overwritten).
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.recognition.landmarks import FEATURE_DIM
from app.recording import find_segments
from nlp.lexicon import load_lexicon

NOTICE = (
    "Combined training set: INCLUDE (Sridhar et al., ACM MM 2020; authors' predefined split, signer independence not verified; treated as "
    "CC BY-NC-SA 4.0, see DATA_NOTICE.md) plus self-recorded takes (landmarks only, split by signer). Not for redistribution beyond those terms."
)


class ManifestError(ValueError):
    pass


def trim_take(features: np.ndarray) -> tuple[np.ndarray | None, str]:
    """Drop frames without a body pose and cut the take to the sign. Returns (rows, note); rows is None when no sign movement is found."""
    if features.ndim != 2 or features.shape[1] != FEATURE_DIM:
        return None, "wrong shape"
    ok = (features[:, : 33 * 3] != 0).any(axis=1)
    rows = features[ok]
    if len(rows) == 0:
        return None, "no frame with a body pose"
    segs = find_segments(rows, np.ones(len(rows), dtype=bool))
    if not segs:
        return None, "no sign movement"
    start, end = min(s.start for s in segs), max(s.end for s in segs)
    return rows[start : end + 1].astype(np.float32), f"{len(segs)} segment(s)" if len(segs) > 1 else "ok"


def class_label(gloss: str, lex) -> str:
    """INCLUDE class name for INCLUDE glosses (the take joins that class), the gloss itself for grammar words."""
    sign = lex.signs.get(gloss)
    return sign.label if sign is not None and sign.source == "include" else gloss


def read_takes(recorded: Path) -> list[tuple[str, str, Path]]:
    """(signer, gloss, feature file) for data/recorded/<SIGNER>/<GLOSS>/*.npy. The single sign layout without a signer folder is not used here."""
    out = []
    for signer_dir in sorted(p for p in recorded.iterdir() if p.is_dir()):
        for gloss_dir in sorted(p for p in signer_dir.iterdir() if p.is_dir()):
            out += [(signer_dir.name, gloss_dir.name, f) for f in sorted(gloss_dir.glob("*.npy"))]
    return out


def build(include_manifest: Path, recorded: Path, out: Path, test_signers: list[str], val_signers: list[str], min_train_takes: int = 5,
          lex=None) -> dict:
    lex = lex or load_lexicon()
    test_signers, val_signers = [s.upper() for s in test_signers], [s.upper() for s in val_signers]
    if out.exists():
        raise ManifestError(f"{out} already exists; nothing is overwritten. Choose a new folder.")
    if not test_signers:
        raise ManifestError("give at least one --test-signer: the self-recorded test split must be a person the model never trains on")
    if set(test_signers) & set(val_signers):
        raise ManifestError("a signer cannot be in both the test and the validation split")
    takes = read_takes(recorded) if recorded.is_dir() else []
    signers = sorted({s for s, _, _ in takes})
    missing = [s for s in test_signers + val_signers if s not in signers]
    if missing:
        raise ManifestError(f"no recordings found for signer(s) {missing}; recorded signers are {signers}")
    train_signers = [s for s in signers if s not in test_signers and s not in val_signers]
    if not train_signers:
        raise ManifestError("no signer is left for training; record more signers or use fewer held-out ones")

    rows = [r for r in csv.DictReader(include_manifest.open(newline="", encoding="utf-8"))]
    out.mkdir(parents=True)
    split_of = {s: ("test" if s in test_signers else "val" if s in val_signers else "train") for s in signers}
    kept: list[dict] = []
    skipped: list[dict] = []
    for signer, gloss, f in takes:
        feats = np.load(f)
        trimmed, note = trim_take(feats)
        if trimmed is None:
            skipped.append({"signer": signer, "gloss": gloss, "file": f.name, "reason": note})
            continue
        dest = out / "recorded_features" / signer / gloss / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        np.save(dest, trimmed)
        kept.append({"path": str(dest.relative_to(out)).replace("\\", "/"), "label": class_label(gloss, lex), "signer_id": signer, "split": split_of[signer],
                     "gloss": gloss, "frames_before": int(len(feats)), "frames_after": int(len(trimmed)), "note": note})

    # classes with too few training takes would only add noise: report them and leave their takes out of every split
    train_counts = Counter(k["label"] for k in kept if k["split"] == "train")
    thin = sorted(l for l in {k["label"] for k in kept} if train_counts[l] < min_train_takes)
    kept_final = [k for k in kept if k["label"] not in thin]

    include_dir = include_manifest.parent
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "label", "signer_id", "split"])
        for r in rows:  # INCLUDE: unchanged, paths made relative to the new folder
            rel = Path(os.path.relpath(include_dir / r["path"], out)).as_posix()
            w.writerow([rel, r["label"], r["signer_id"], r["split"]])
        for k in kept_final:
            w.writerow([k["path"], k["label"], k["signer_id"], k["split"]])
    (out / "dataset_info.json").write_text(json.dumps({"name": "INCLUDE + self-recorded (combined)", "language": "ISL", "license": NOTICE,
                                                        "source_url": "https://zenodo.org/records/4010759"}, indent=2), encoding="utf-8")

    new_labels = sorted({k["label"] for k in kept_final} - {r["label"] for r in rows})
    per_split = Counter(k["split"] for k in kept_final)
    by_signer = defaultdict(Counter)
    for k in kept_final:
        by_signer[k["signer_id"]][k["split"]] += 1
    report = {
        "include_rows": len(rows),
        "self_recorded_rows": len(kept_final),
        "self_recorded_per_split": dict(per_split),
        "signers": {"train": train_signers, "val": val_signers, "test": test_signers},
        "takes_per_signer": {s: sum(c.values()) for s, c in by_signer.items()},
        "new_classes": new_labels,
        "extra_takes_for_include_classes": sorted({k["label"] for k in kept_final} & {r["label"] for r in rows}),
        "classes_left_out_for_too_few_training_takes": thin,
        "min_train_takes": min_train_takes,
        "takes_without_sign_movement": skipped,
        "trimmed_frames": {"before": sum(k["frames_before"] for k in kept), "after": sum(k["frames_after"] for k in kept)},
        "takes_with_several_segments": sum(1 for k in kept if k["note"] != "ok"),
        "test_classes_without_a_test_take": sorted({k["label"] for k in kept_final if k["split"] == "train"} - {k["label"] for k in kept_final if k["split"] == "test"}),
        "val_classes_without_a_val_take": sorted({k["label"] for k in kept_final if k["split"] == "train"} - {k["label"] for k in kept_final if k["split"] == "val"}),
    }
    # the guarantee the whole design rests on: one signer, one split
    seen: dict[str, set[str]] = defaultdict(set)
    for k in kept_final:
        seen[k["signer_id"]].add(k["split"])
    assert all(len(v) == 1 for v in seen.values()), "a signer appears in more than one split"
    (out / "combined_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--include-manifest", type=Path, required=True)
    ap.add_argument("--recorded", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--test-signer", nargs="+", required=True)
    ap.add_argument("--val-signer", nargs="*", default=[])
    ap.add_argument("--min-train-takes", type=int, default=5)
    a = ap.parse_args()
    try:
        r = build(a.include_manifest, a.recorded, a.out, a.test_signer, a.val_signer, a.min_train_takes)
    except ManifestError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: r[k] for k in ("include_rows", "self_recorded_rows", "self_recorded_per_split", "signers", "new_classes")}, indent=2))
    print(f"report: {a.out / 'combined_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
