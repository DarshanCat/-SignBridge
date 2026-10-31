"""Retarget a starter vocabulary from INCLUDE training samples. Run from backend/:

    python -m retarget.make_vocabulary --manifest ..\\data\\processed\\include\\manifest.csv --parts ..\\data\\processed\\include\\_parts
                                       --out ..\\frontend\\public\\animations --glosses HELLO THANK-YOU ...

For each gloss it takes the TRAINING split samples of the matching INCLUDE class and picks the one with the fewest missing-hand frames
(primary: frames with no hand detected at all; then frames missing either hand, counted per hand; then the longer sequence; then the file
name), retargets it, and records the chosen sample in the clip JSON (`source.source_sample`). It also writes `index.json`, a map from
gloss to clip file with the same provenance. Data files are only read. Every clip is `not_signer_reviewed`; none is a verified sign.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

from app.recognition.preprocess import hand_missing_mask
from nlp.lexicon import load_lexicon
from retarget.clip_builder import build_clip

LICENSE_NOTE = (
    "Derived from INCLUDE (Sridhar et al., ACM MM 2020). Treated as CC BY-NC-SA 4.0: non-commercial only, with attribution, share alike (see DATA_NOTICE.md). The dataset's own licence is unresolved (CC BY 4.0 per Zenodo, CC BY-NC-SA 4.0 per a third party page)."
)


def missing_stats(seq: np.ndarray) -> dict:
    left, right = hand_missing_mask(seq)
    return {
        "frames": int(len(seq)),
        "no_hand_frames": int((left & right).sum()),
        "left_missing_frames": int(left.sum()),
        "right_missing_frames": int(right.sum()),
    }


def rank_key(stats: dict, name: str) -> tuple:
    """Smaller is better: no-hand frames, then left plus right missing frames, then longer sequences, then file name."""
    return (stats["no_hand_frames"], stats["left_missing_frames"] + stats["right_missing_frames"], -stats["frames"], name)


def pick_sample(candidates: list[tuple[str, np.ndarray]]) -> tuple[str, np.ndarray, dict, int]:
    ranked = sorted(((rank_key(missing_stats(a), n), n, a) for n, a in candidates), key=lambda t: t[0])
    _, name, arr = ranked[0]
    return name, arr, missing_stats(arr), len(candidates)


def video_names(parts_dir: Path) -> dict[str, str]:
    """feature file name -> original video path inside the INCLUDE archive (only the path text, not the video)."""
    out: dict[str, str] = {}
    for p in sorted(parts_dir.glob("*.csv")):
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["npy"]:
                    out[r["npy"]] = r["member"]
    return out


REGISTRY_ATTRIBUTION = "Sridhar, Ganesan, Kumar, Khapra: INCLUDE, ACM Multimedia 2020 (DOI 10.1145/3394171.3413528)"
REGISTRY_LICENSE = LICENSE_NOTE


def register(registry_path: Path, index: dict[str, dict], lex) -> None:
    """Add or update one registry record per built clip. Status is clip_unreviewed; nothing here can mark a sign verified."""
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    by = {s["gloss"]: s for s in reg["signs"]}
    for gloss, e in index.items():
        rec = by.get(gloss)
        if rec is None:
            rec = {"gloss": gloss, "meaning": lex.signs[gloss].label.lower(), "context": "INCLUDE class name; sign, context and handshape not reviewed by an ISL signer"}
            reg["signs"].append(rec)
            by[gloss] = rec
        rec.update({
            "reference_source": "INCLUDE sample " + e["source_sample"]["video"], "asset_id": gloss.lower(), "license": REGISTRY_LICENSE,
            "attribution": REGISTRY_ATTRIBUTION, "verification_status": "clip_unreviewed", "visually_reviewed": False, "signer_reviewed": False,
        })
    registry_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--parts", type=Path, nargs="+", required=True, help="part record folder(s) mapping feature files to video paths")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--glosses", nargs="+", help="glosses to build (default: every INCLUDE sign in the gloss dictionary with --all-include)")
    ap.add_argument("--all-include", action="store_true", help="build every INCLUDE sign that appears in config/gloss_dictionary.json")
    ap.add_argument("--registry", type=Path, help="sign registry to update (clip_unreviewed records); omit to leave it untouched")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--stride", type=int, default=2)
    a = ap.parse_args()

    lex = load_lexicon()
    if a.all_include:
        a.glosses = sorted(g for g, sg in lex.signs.items() if sg.source == "include")
    if not a.glosses:
        print("Error: give --glosses or --all-include", file=sys.stderr)
        return 2
    rows = list(csv.DictReader(a.manifest.open(newline="", encoding="utf-8")))
    members: dict[str, str] = {}
    for pdir in a.parts:
        members |= video_names(pdir)
    index: dict[str, dict] = {}
    problems: list[str] = []
    for gloss in a.glosses:
        sign = lex.signs.get(gloss)
        if sign is None or sign.source != "include":
            problems.append(f"{gloss}: not an INCLUDE class in the dictionary")
            continue
        cands = [
            (r["path"], np.load(a.manifest.parent / r["path"]))
            for r in rows if r["split"] == "train" and r["label"].lower() == sign.label.lower()
        ]
        if not cands:
            problems.append(f"{gloss}: no training samples for class {sign.label!r}")
            continue
        name, seq, stats, n = pick_sample(cands)
        video = members.get(Path(name).name, "unknown")
        sample = {"feature_file": Path(name).name, "video": video, "split": "train", "class": sign.label,
                  "candidates_considered": n, **stats, "selection": "fewest frames with no hand detected, then fewest missing-hand frames"}
        clip = build_clip(
            seq, gloss, fps=a.fps, stride=a.stride, author="SignBridge automatic retarget", license_text=LICENSE_NOTE,
            description=f"UNREVIEWED automatic retarget of one INCLUDE training sample ({video}); fps {a.fps} assumed, stride {a.stride}; not a verified sign",
            sample=sample,
        )
        file = f"{gloss.lower()}.json"
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / file).write_text(json.dumps(clip), encoding="utf-8")
        index[gloss] = {"file": file, "duration": clip["duration"], "review_status": "not_signer_reviewed", "source_sample": sample}
        print(f"{gloss}: {video} ({stats['no_hand_frames']} no-hand frames of {stats['frames']}, {n} candidates) -> {file}")
    if index:
        (a.out / "index.json").write_text(
            json.dumps({"version": 1, "note": "Automatic retargets from INCLUDE; none is signer reviewed or a verified sign.", "clips": index}, indent=1),
            encoding="utf-8",
        )
    if index and a.registry:
        register(a.registry, index, lex)
    for p in problems:
        print("PROBLEM:", p, file=sys.stderr)
    print(f"built {len(index)} clip(s); {len(problems)} gloss(es) without a clip")
    return 2 if problems and not a.all_include else 0


if __name__ == "__main__":
    sys.exit(main())
