"""Evaluate live sign segmentation plus recognition on streams built from real INCLUDE samples. Run from backend/:

    python -m training.eval_segmentation --manifest ..\\data\\processed\\include_v2\\manifest.csv --model-dir models --split val --streams 80 --gap 10

Each stream joins 3 to 5 real samples of different classes; between two samples `gap` extra rest frames are inserted (a copy of the last
frame of the earlier sample, which is a still pose with the hands down, plus 0.003 noise). Ground truth for a sign is the span of its sample
in the stream. The stream goes through the same segmenter and classifier code as the WebSocket (`app.services.live_service`).

Tune on the validation split. The test split is for ONE final run (CLAUDE.md: the test split is evaluated once per model); this script prints
the split it used so the report can say so. Nothing here changes the model or the data.
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np

from app.recognition.segmenter import SegmenterConfig, SignSegmenter
from app.services.live_service import LiveSession, segment_events
from nlp.lexicon import load_lexicon


def load_split(manifest: Path, split: str) -> list[tuple[str, np.ndarray]]:
    rows = [r for r in csv.DictReader(manifest.open(newline="", encoding="utf-8")) if r["split"] == split]
    return [(r["label"], np.load(manifest.parent / r["path"]).astype(np.float32)) for r in rows]


def build_stream(samples: list[tuple[str, np.ndarray]], rng: random.Random, n_signs: int, gap: int):
    """Returns (rows, truth) with truth = [(label, start, end)] in stream (usable frame) indices."""
    chosen, used = [], set()
    pool = list(range(len(samples)))
    rng.shuffle(pool)
    for i in pool:
        if samples[i][0] not in used:
            used.add(samples[i][0])
            chosen.append(samples[i])
        if len(chosen) == n_signs:
            break
    rows, truth = [], []
    noise = np.random.default_rng(rng.randrange(1 << 30))
    for k, (label, feats) in enumerate(chosen):
        if k and gap:
            rest = np.repeat(rows[-1][None, :], gap, axis=0) + noise.normal(0, 0.003, (gap, feats.shape[1])).astype(np.float32)
            rows.extend(list(rest))
        start = len(rows)
        rows.extend(list(feats))
        truth.append((label, start, len(rows) - 1))
    return rows, truth


def iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)
    union = (a[1] - a[0] + 1) + (b[1] - b[0] + 1) - inter
    return inter / union if union else 0.0


def overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)


def score_stream(truth, events) -> dict:
    segs = [(e["segment"]["start"], e["segment"]["end"], e) for e in events if e["type"] in ("sign", "ignored")]
    out = Counter()
    out["true_signs"] = len(truth)
    out["segments"] = len(segs)
    pred_seq = []
    for label, ts, te in truth:
        hits = [s for s in segs if overlap((ts, te), (s[0], s[1])) > 0]
        good = [s for s in hits if iou((ts, te), (s[0], s[1])) >= 0.5]
        if not hits:
            out["missed"] += 1
        elif len(hits) >= 2:
            out["fragmented"] += 1
        if len(good) == 1 and len(hits) == 1:
            out["split_correct"] += 1
            e = good[0][2]
            if e["type"] == "sign" and e["accepted"]:
                out["recognized_correct" if e["label"] == label else "recognized_wrong"] += 1
            else:
                out["unrecognized"] += 1
    for s in segs:
        touching = [t for t in truth if overlap((t[1], t[2]), (s[0], s[1])) > 0]
        if not touching:
            out["extra_segments"] += 1
        elif len(touching) >= 2:
            out["merged_segments"] += 1
    for s in sorted(segs, key=lambda x: x[0]):
        if s[2]["type"] == "sign" and s[2]["accepted"]:
            pred_seq.append(s[2]["label"])
    out["sentence_exact"] = int(pred_seq == [t[0] for t in truth])
    return dict(out)


def run(samples, model_dir: Path, cfg: SegmenterConfig, streams: int, gap: int, seed: int, lo: int = 3, hi: int = 5) -> dict:
    lex = load_lexicon()
    rng = random.Random(seed)
    total = Counter()
    for _ in range(streams):
        rows, truth = build_stream(samples, rng, rng.randint(lo, hi), gap)
        session = LiveSession(segmenter=SignSegmenter(cfg))
        events = segment_events(rows, session, model_dir, lex, 0.5)
        events += [{"type": "sign", **e} for e in []]
        for seg in session.segmenter.flush():  # a sign still open at the end of the stream
            from app.services.live_service import _classify

            pred = _classify(seg.features, session, model_dir, lex, 0.5, True)
            pred["type"] = "sign"
            pred["segment"] = {"start": seg.start, "end": seg.end, "frames": seg.frames}
            events.append(pred)
        total.update(score_stream(truth, events))
        total["streams"] += 1
    return dict(total)


def report(t: dict, label: str) -> str:
    n = t["true_signs"]
    p = lambda k: f"{t.get(k, 0)} ({100 * t.get(k, 0) / n:.1f}%)"  # noqa: E731
    return "\n".join([
        f"[{label}] {t['streams']} streams, {n} real signs, {t['segments']} segments found",
        f"  split correctly (one segment, IoU >= 0.5): {p('split_correct')}",
        f"    recognized correctly (accepted at the live threshold): {p('recognized_correct')}",
        f"    accepted but wrong label: {p('recognized_wrong')}",
        f"    returned UNRECOGNIZED: {p('unrecognized')}",
        f"  missed (no segment overlaps): {p('missed')}   fragmented (2 or more segments): {p('fragmented')}",
        f"  segments covering 2 or more signs (merged): {t.get('merged_segments', 0)}   segments touching no sign: {t.get('extra_segments', 0)}",
        f"  whole sentence exactly right: {t.get('sentence_exact', 0)} of {t['streams']} streams",
    ])


def parse_cfg(text: str) -> SegmenterConfig:
    cfg = SegmenterConfig()
    kv = {}
    for item in filter(None, text.split(",")):
        k, _, v = item.partition("=")
        kv[k] = type(getattr(cfg, k))(v)
    return replace(cfg, **kv)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--model-dir", type=Path, default=Path("models"))
    ap.add_argument("--split", choices=["train", "val", "test"], default="val")
    ap.add_argument("--streams", type=int, default=80)
    ap.add_argument("--gap", type=int, nargs="+", default=[0, 10, 20])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--cfg", default="", help="segmenter overrides, for example rest_y=1.6,end_frames=6")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    cfg = parse_cfg(a.cfg)
    samples = load_split(a.manifest, a.split)
    results = {}
    print(f"split: {a.split} ({len(samples)} samples), segmenter: {cfg}")
    for g in a.gap:
        t = run(samples, a.model_dir, cfg, a.streams, g, a.seed)
        results[f"gap{g}"] = t
        print(report(t, f"{a.split}, {g} extra rest frames between signs"))
    if a.json:
        a.json.write_text(json.dumps({"split": a.split, "cfg": cfg.__dict__, "results": results}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
