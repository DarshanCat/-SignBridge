"""Combined INCLUDE plus self-recorded manifest with a signer-level split, built from synthetic features in temporary folders."""

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from app.recognition.landmarks import FEATURE_DIM
from app.recognition.segmenter import LEFT_WRIST_X, LEFT_WRIST_Y, RIGHT_WRIST_X, RIGHT_WRIST_Y
from training.data import read_manifest, split_samples
from training.make_combined_manifest import ManifestError, build, trim_take


def row(wrist_y: float, wrist_x: float = 0.0, hands: bool = True) -> np.ndarray:
    r = np.zeros(FEATURE_DIM, dtype=np.float32)
    r[11 * 3], r[12 * 3] = 0.5, -0.5  # shoulders: a usable body pose
    r[LEFT_WRIST_X], r[LEFT_WRIST_Y], r[RIGHT_WRIST_X], r[RIGHT_WRIST_Y] = wrist_x, wrist_y, -wrist_x, wrist_y
    if hands:
        r[99:] = 0.1
    return r


def take(rest_before: int = 15, sign: int = 24, rest_after: int = 15) -> np.ndarray:
    rows = [row(2.8) for _ in range(rest_before)]
    rows += [row(0.5 + 0.3 * np.sin(i / 2), 0.2 * np.cos(i)) for i in range(sign)]
    rows += [row(2.8) for _ in range(rest_after)]
    return np.stack(rows)


def make_tree(tmp: Path, takes_per: int = 6) -> tuple[Path, Path]:
    inc = tmp / "include_v2"
    inc.mkdir()
    rows = []
    for split, n in (("train", 3), ("val", 1), ("test", 1)):
        for i in range(n):
            name = f"{split}{i}.npy"
            np.save(inc / name, take())
            rows.append([name, "Hello", "unknown", split])
    with (inc / "manifest.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "label", "signer_id", "split"])
        w.writerows(rows)
    rec = tmp / "recorded"
    for signer in ("P01", "P02", "P03", "P04"):
        for gloss in ("WHERE", "HELLO"):
            d = rec / signer / gloss
            d.mkdir(parents=True)
            for i in range(takes_per):
                np.save(d / f"2026{i:04d}.npy", take(rest_before=10 + i))
    return inc / "manifest.csv", rec


def test_trim_cuts_to_the_sign_with_padding_and_rejects_takes_without_movement() -> None:
    t = take()
    trimmed, note = trim_take(t)
    assert note == "ok" and 24 <= len(trimmed) <= 24 + 5 + 4 + 2 and len(trimmed) < len(t)
    idle = np.stack([row(2.8) for _ in range(40)])
    assert trim_take(idle) == (None, "no sign movement")
    nopose = np.zeros((30, FEATURE_DIM), dtype=np.float32)
    assert trim_take(nopose)[0] is None
    with_gap = np.concatenate([t[:20], np.zeros((5, FEATURE_DIM), dtype=np.float32), t[20:]])  # frames without a pose are dropped first
    assert trim_take(with_gap)[0] is not None


def test_signer_level_split_labels_and_untouched_sources(tmp_path) -> None:
    man, rec = make_tree(tmp_path)
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    out = tmp_path / "combined"
    report = build(man, rec, out, ["P04"], ["P03"], min_train_takes=5)
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if "combined" not in p.parts) == before  # sources unchanged
    assert report["signers"] == {"train": ["P01", "P02"], "val": ["P03"], "test": ["P04"]}
    rows = list(csv.DictReader((out / "manifest.csv").open()))
    inc = [r for r in rows if r["signer_id"] == "unknown"]
    own = [r for r in rows if r["signer_id"] != "unknown"]
    assert len(inc) == 5 and {r["split"] for r in inc} == {"train", "val", "test"}  # the authors' split is kept
    assert len(own) == 4 * 2 * 6
    split_by_signer = {s: {r["split"] for r in own if r["signer_id"] == s} for s in ("P01", "P02", "P03", "P04")}
    assert split_by_signer == {"P01": {"train"}, "P02": {"train"}, "P03": {"val"}, "P04": {"test"}}  # one signer, one split
    assert {r["label"] for r in own} == {"WHERE", "Hello"}  # the INCLUDE gloss joins the INCLUDE class, the grammar word keeps its name
    assert report["new_classes"] == ["WHERE"] and report["extra_takes_for_include_classes"] == ["Hello"]
    for r in rows:  # every referenced file exists and has the 225 feature layout
        assert np.load(out / r["path"]).shape[1] == FEATURE_DIM
    assert report["trimmed_frames"]["after"] < report["trimmed_frames"]["before"]
    # the existing loader accepts the manifest as a predefined split
    samples = read_manifest(out / "manifest.csv")
    splits, method = split_samples(samples, 0)
    assert method == "predefined" and all(splits[k] for k in ("train", "val", "test"))
    assert "CC BY-NC-SA" in json.loads((out / "dataset_info.json").read_text())["license"]


def test_refuses_to_overwrite_and_rejects_bad_signer_choices(tmp_path) -> None:
    man, rec = make_tree(tmp_path)
    out = tmp_path / "combined"
    build(man, rec, out, ["P04"], ["P03"])
    with pytest.raises(ManifestError, match="already exists"):
        build(man, rec, out, ["P04"], ["P03"])
    with pytest.raises(ManifestError, match="at least one --test-signer"):
        build(man, rec, tmp_path / "c2", [], ["P03"])
    with pytest.raises(ManifestError, match="both"):
        build(man, rec, tmp_path / "c3", ["P04"], ["P04"])
    with pytest.raises(ManifestError, match="no recordings found"):
        build(man, rec, tmp_path / "c4", ["P09"], [])
    with pytest.raises(ManifestError, match="no signer is left"):
        build(man, rec, tmp_path / "c5", ["P01", "P02", "P03"], ["P04"])
    assert not (tmp_path / "c2").exists() and not (tmp_path / "c4").exists()


def test_takes_without_movement_are_reported_and_thin_classes_are_left_out(tmp_path) -> None:
    man, rec = make_tree(tmp_path, takes_per=3)
    for i in range(2):  # an idle take for P01 and a class with very few takes
        np.save(rec / "P01" / "WHERE" / f"idle{i}.npy", np.stack([row(2.8) for _ in range(40)]))
    d = rec / "P01" / "RARE"
    d.mkdir()
    np.save(d / "a.npy", take())
    report = build(man, rec, tmp_path / "combined", ["P04"], ["P03"], min_train_takes=5)
    assert len(report["takes_without_sign_movement"]) == 2 and report["takes_without_sign_movement"][0]["reason"] == "no sign movement"
    assert "RARE" in report["classes_left_out_for_too_few_training_takes"]
    rows = list(csv.DictReader((tmp_path / "combined" / "manifest.csv").open()))
    assert "RARE" not in {r["label"] for r in rows}
    assert report["classes_left_out_for_too_few_training_takes"] == ["RARE"]  # WHERE keeps 2 training signers x 3 takes = 6 >= 5


# fixed signer roles ----------------------------------------------------------------------------------------------------------------------------

def test_shipped_roles_are_the_decided_ones_and_disjoint() -> None:
    from training.make_combined_manifest import load_roles

    roles = load_roles()
    assert roles == {"train": ["S01", "S02", "S03"], "val": ["S04"], "test": ["S05"]}
    assert not (set(roles["train"]) & set(roles["val"])) and not (set(roles["train"]) & set(roles["test"])) and not (set(roles["val"]) & set(roles["test"]))


def test_command_line_cannot_change_the_fixed_roles() -> None:
    from training.make_combined_manifest import resolve_roles

    roles = {"train": ["S01", "S02", "S03"], "val": ["S04"], "test": ["S05"]}
    assert resolve_roles(roles, None, None) == (["S05"], ["S04"], ["S01", "S02", "S03"])
    assert resolve_roles(roles, ["s05"], ["s04"]) == (["S05"], ["S04"], ["S01", "S02", "S03"])  # matching values are fine, case does not matter
    with pytest.raises(ManifestError, match="test signer"):
        resolve_roles(roles, ["S03"], None)
    with pytest.raises(ManifestError, match="validation signer"):
        resolve_roles(roles, None, ["S01"])
    with pytest.raises(ManifestError, match="no signer_roles.json"):
        resolve_roles(None, None, None)
    assert resolve_roles(None, ["P4"], ["P3"]) == (["P4"], ["P3"], None)  # without a roles file the old behaviour remains


def test_a_recorded_signer_without_a_role_is_refused(tmp_path) -> None:
    man, rec = make_tree(tmp_path)  # signers P01 to P04
    with pytest.raises(ManifestError, match="no role"):
        build(man, rec, tmp_path / "c", ["P04"], ["P03"], train_signers=["P01"])  # P02 has no role
    ok = build(man, rec, tmp_path / "c2", ["P04"], ["P03"], train_signers=["P01", "P02", "P09"])  # a role without recordings yet is fine
    assert ok["signers"]["train"] == ["P01", "P02"]
