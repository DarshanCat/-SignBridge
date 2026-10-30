import json

import numpy as np

from app.core.config import BACKEND_DIR
from app.recognition.landmarks import FEATURE_DIM
from retarget.make_vocabulary import missing_stats, pick_sample, rank_key

ANIM = BACKEND_DIR.parent / "frontend" / "public" / "animations"


def seq(t: int, left_missing: int = 0, right_missing: int = 0, both_missing: int = 0) -> np.ndarray:
    x = np.ones((t, FEATURE_DIM), dtype=np.float32)
    x[:left_missing, 99:162] = 0
    x[left_missing : left_missing + right_missing, 162:] = 0
    start = left_missing + right_missing
    x[start : start + both_missing, 99:] = 0
    return x


def test_missing_stats_counts_frames() -> None:
    s = missing_stats(seq(20, left_missing=3, right_missing=2, both_missing=4))
    assert s == {"frames": 20, "no_hand_frames": 4, "left_missing_frames": 7, "right_missing_frames": 6}


def test_pick_sample_prefers_fewest_no_hand_frames_then_fewest_missing_then_longer() -> None:
    cands = [("a.npy", seq(30, both_missing=3)), ("b.npy", seq(30, left_missing=8)), ("c.npy", seq(30, left_missing=2)), ("d.npy", seq(40, left_missing=2))]
    name, _, stats, n = pick_sample(cands)
    assert name == "d.npy" and stats["no_hand_frames"] == 0 and n == 4  # c and d tie on missing frames, d is longer
    assert rank_key({"no_hand_frames": 0, "left_missing_frames": 0, "right_missing_frames": 0, "frames": 5}, "z") < rank_key(
        {"no_hand_frames": 1, "left_missing_frames": 0, "right_missing_frames": 0, "frames": 50}, "a")


def test_shipped_vocabulary_index_matches_the_clip_files_and_records_the_sample() -> None:
    idx = json.loads((ANIM / "index.json").read_text(encoding="utf-8"))["clips"]
    assert len(idx) == 10 and {"HELLO", "THANK-YOU", "HOSPITAL", "MARKET", "YESTERDAY", "I", "YOU", "DOCTOR", "BANK", "TOMORROW"} == set(idx)
    for gloss, e in idx.items():
        clip = json.loads((ANIM / e["file"]).read_text(encoding="utf-8"))
        assert clip["gloss"] == gloss and clip["source"]["review_status"] == "not_signer_reviewed"
        sample = clip["source"]["source_sample"]
        assert sample == e["source_sample"] and sample["split"] == "train" and sample["video"].endswith(".MOV")
        assert sample["feature_file"].endswith(".npy") and sample["candidates_considered"] >= 1
