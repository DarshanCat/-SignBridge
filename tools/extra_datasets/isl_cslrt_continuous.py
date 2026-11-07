"""ISL-CSLTR continuous sentence test, exactly as fixed in docs/evaluation/ISL_CSLRT_PROTOCOL.md. Run from backend/ with its virtual environment:

    python ..\\tools\\extra_datasets\\isl_cslrt_continuous.py extract    # fetch the selected videos one by one (byte ranges), keep only landmarks
    python ..\\tools\\extra_datasets\\isl_cslrt_continuous.py evaluate   # one pass of the live model over them, writes docs/evaluation/isl_cslrt_continuous.*

Resumable: a video whose landmark file exists is not fetched again. The model, threshold and segmenter are the live ones and are not changed here."""
import collections
import csv
import json
import math
import posixpath
import re
import shutil
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).parent))

DATA = ROOT / "data" / "datasets" / "isl_cslrt"
OUT = ROOT / "data" / "processed" / "isl_cslrt"
URL = "https://prod-dcd-datasets-public-files-eu-west-1.s3.eu-west-1.amazonaws.com/5de8c65d-30ba-4362-941f-47d61d435aa0"
SIZE = 8905822924
PER_SENTENCE = 3


def norm_sentence(s: str) -> str:
    return re.sub(r"\s+", "", s.strip().lower())


def corpus_glosses(g: str) -> list[str]:
    return re.sub(r"[.,]", "", g).split()


def join_class_glosses(tokens: list[str], classes: set[str]) -> list[str]:
    """Protocol normalization: neighbouring tokens that form a class gloss with hyphens become that gloss (THANK YOU to THANK-YOU)."""
    out, i = [], 0
    while i < len(tokens):
        for n in (3, 2):
            cand = "-".join(tokens[i : i + n])
            if len(tokens[i : i + n]) == n and cand in classes:
                out.append(cand)
                i += n
                break
        else:
            out.append(tokens[i])
            i += 1
    return out


def selection():
    from nlp.gloss_forms import to_gloss

    classes = {to_gloss(c) for c in json.loads((ROOT / "backend" / "models" / "labels.json").read_text(encoding="utf-8"))["classes"]}
    rows = list(csv.DictReader((DATA / "ISL Corpus sign glosses.csv").open(encoding="utf-8")))
    members = json.loads((DATA / "members.json").read_text(encoding="utf-8"))
    folders = collections.defaultdict(list)
    for m in members:
        if m["name"].lower().endswith(".mp4"):
            folders[norm_sentence(posixpath.basename(posixpath.dirname(m["name"])))].append(m)
    chosen = []
    for r in rows:
        toks = join_class_glosses(corpus_glosses(r["SIGN GLOSSES"]), classes)
        if not any(t in classes for t in toks):
            continue
        for m in sorted(folders.get(norm_sentence(r["Sentence"]), []), key=lambda x: x["name"])[:PER_SENTENCE]:
            chosen.append({"sentence": r["Sentence"].strip(), "glosses": toks, "member": m["name"], "size": m["size"], "id": f"{len(chosen):03d}"})
    return chosen, classes


def _extract(args):
    path, out_npy = args
    from training.data import DatasetError
    from training.video_features import video_to_features
    import numpy as np

    try:
        feats = video_to_features(Path(path), 2)
        np.save(out_npy, feats)
        return out_npy, int(feats.shape[0]), ""
    except DatasetError as exc:
        return out_npy, 0, str(exc)
    finally:
        Path(path).unlink(missing_ok=True)


def extract():
    from range_zip import RangeFile

    chosen, _ = selection()
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / "data" / "raw" / "isl_cslrt_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (OUT / "selection.json").write_text(json.dumps(chosen, indent=1), encoding="utf-8")
    z = zipfile.ZipFile(RangeFile(URL, SIZE, chunk=1 << 22))
    rf = z.fp
    todo = [c for c in chosen if not (OUT / f"{c['id']}.npy").exists()]
    print(f"{len(chosen)} videos selected, {len(todo)} to fetch ({sum(c['size'] for c in todo) / 1e9:.2f} GB)", flush=True)
    failures = {}
    with ProcessPoolExecutor(max_workers=10) as pool:
        pending = []
        for n, c in enumerate(todo, 1):
            dest = tmp / f"{c['id']}{posixpath.splitext(c['member'])[1]}"
            with z.open(c["member"]) as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            rf._cache.clear()  # keep memory flat
            pending.append(pool.submit(_extract, (str(dest), str(OUT / f"{c['id']}.npy"))))
            if n % 20 == 0:
                print(f"fetched {n}/{len(todo)}, {rf.fetched / 1e9:.2f} GB transferred", flush=True)
        for c, f in zip(todo, pending):
            _, frames, msg = f.result()
            if msg:
                failures[c["id"]] = msg
    (OUT / "extract_failures.json").write_text(json.dumps(failures, indent=1), encoding="utf-8")
    print(f"done: {len(todo) - len(failures)} usable, {len(failures)} failed, {rf.fetched / 1e9:.2f} GB transferred", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)


def spearman(a, b):
    def rank(x):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r = [0.0] * len(x)
        i = 0
        while i < len(x):
            j = i
            while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else float("nan")


def evaluate():
    import numpy as np

    from app.core.config import get_settings
    from app.recognition.segmenter import SignSegmenter
    from app.services.live_service import LiveSession, _classify, load_threshold, segment_events
    from nlp.gloss_forms import to_gloss
    from nlp.lexicon import load_lexicon

    s = get_settings()
    lex = load_lexicon(s.gloss_dictionary)
    threshold, source = load_threshold(s.model_dir, s.min_confidence)
    chosen, classes = selection()
    failures = json.loads((OUT / "extract_failures.json").read_text(encoding="utf-8")) if (OUT / "extract_failures.json").exists() else {}
    per, missing = [], []
    for c in chosen:
        f = OUT / f"{c['id']}.npy"
        if not f.exists():
            missing.append(c["id"])
            continue
        rows = list(np.load(f).astype(np.float32))
        session = LiveSession(segmenter=SignSegmenter())
        events = segment_events(rows, session, s.model_dir, lex, threshold)
        for seg in session.segmenter.flush():
            hands = int(((seg.features[:, 99:] != 0).any(axis=1)).sum())
            if len(seg.features) >= 8 and hands >= 4:
                pred = _classify(seg.features.astype(np.float32), session, s.model_dir, lex, threshold, True)
                pred.update(type="sign", segment={"start": seg.start, "end": seg.end, "frames": seg.frames})
                events.append(pred)
        signs = [e for e in events if e["type"] == "sign"]
        answers = [to_gloss(e["label"]) for e in signs if e.get("accepted")]
        per.append({"id": c["id"], "sentence": c["sentence"], "kind": "camera" if c["member"].endswith(".MP4") else "small", "glosses": c["glosses"],
                    "segments": len(events), "signs": len(signs), "answered": answers, "frames": len(rows)})
    n_gloss = [len(p["glosses"]) for p in per]
    n_seg = [p["segments"] for p in per]
    covered_total = covered_found = 0
    answered = wrong = 0
    by_kind = collections.defaultdict(lambda: [0, 0, 0])  # answered, wrong, segments
    for p in per:
        cov = collections.Counter(t for t in p["glosses"] if t in classes)
        got = collections.Counter(p["answered"])
        covered_total += sum(cov.values())
        covered_found += sum((cov & got).values())
        ref = set(p["glosses"])
        for a in p["answered"]:
            answered += 1
            wrong += a not in ref
            by_kind[p["kind"]][0] += 1
            by_kind[p["kind"]][1] += a not in ref
        by_kind[p["kind"]][2] += p["signs"]
    total_signs = sum(p["signs"] for p in per)
    full = [p for p in per if all(t in classes for t in p["glosses"])]
    res = {
        "model": {"threshold": threshold, "threshold_source": source}, "videos_selected": len(chosen), "videos_evaluated": len(per), "videos_not_extracted": missing, "extract_failures": failures,
        "segmentation": {"spearman_segments_vs_gloss_tokens": spearman(n_seg, n_gloss), "within_one": sum(abs(a - b) <= 1 for a, b in zip(n_seg, n_gloss)) / len(per),
                         "median_segments": sorted(n_seg)[len(n_seg) // 2], "median_gloss_tokens": sorted(n_gloss)[len(n_gloss) // 2]},
        "covered_sign_recall": {"covered_tokens": covered_total, "found": covered_found, "recall": covered_found / covered_total if covered_total else None},
        "answer_rate": {"signs": total_signs, "answered": answered, "rate": answered / total_signs if total_signs else None},
        "answer_precision": {"answered": answered, "in_sentence_glosses": answered - wrong, "wrong": wrong, "precision": (answered - wrong) / answered if answered else None,
                             "by_video_kind": {k: {"answered": v[0], "wrong": v[1], "signs": v[2]} for k, v in by_kind.items()}},
        "fully_covered_sentences": [{"sentence": p["sentence"], "id": p["id"], "reference": p["glosses"], "answered": p["answered"], "exact": p["answered"] == p["glosses"]} for p in full],
        "per_video": per,
    }
    d = ROOT / "docs" / "evaluation"
    (d / "isl_cslrt_continuous.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "per_video"}, indent=1))


if __name__ == "__main__":
    {"extract": extract, "evaluate": evaluate}[sys.argv[1]]()
