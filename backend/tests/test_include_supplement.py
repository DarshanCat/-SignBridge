import csv
import json

from training.include_supplement import affected_zips, build_manifest, classify, load_listed, stem_key


def make_lists(tmp_path):
    d = tmp_path / "splits"
    d.mkdir()
    (d / "include_train.txt").write_text("Animals/1. Dog/MVI_8560.MOV\nDays_and_Time/Second (Number)/MVI_5506.MOV\n")
    (d / "include_val.txt").write_text("Animals/2. Cat/MVI_8563.MOV\n")
    (d / "include_test.txt").write_text("")
    return d


def test_stem_key_ignores_extension_and_case() -> None:
    assert stem_key("Animals/1. Dog/MVI_8560.MP4") == stem_key("animals/1. dog/mvi_8560.MOV")


def test_classify_extension_fallback_and_skip(tmp_path) -> None:
    listed, by_name = load_listed(make_lists(tmp_path))
    have = {stem_key("Animals/2. Cat/MVI_8563.MOV")}
    assert classify("Animals/1. Dog/MVI_8560.MP4", listed, by_name, have) == ("stem", "animals/1. dog/mvi_8560")
    assert classify("Animals/2. Cat/MVI_8563.MP4", listed, by_name, have)[0] == "have"
    # folder name differs ("81. Second" in the zip, "Second (Number)" in the list): unique file name in the category
    d, k = classify("Days_and_Time/81. Second/MVI_5506.MP4", listed, by_name, have)
    assert d == "filename_fallback" and listed[k][0] == "train"
    assert classify("Animals/9. Bird/MVI_0001.MP4", listed, by_name, have)[0] == "skip"
    assert classify("Animals/1. Dog/MVI_8560.MP4", listed, by_name, have | {"animals/1. dog/mvi_8560"})[0] == "have"


def test_affected_zips_reads_logs(tmp_path) -> None:
    log = tmp_path / "a.log"
    log.write_text("[A_1of2.zip] done: 10/10 usable, 0 videos not in the split lists\n[B_1of1.zip] done: 5/5 usable, 3 videos not in the split lists\n")
    assert affected_zips([log, tmp_path / "missing.log"]) == ["B_1of1.zip"]


def test_build_manifest_keeps_old_folder_untouched_and_references_it(tmp_path) -> None:
    old, new = tmp_path / "include", tmp_path / "include_v2"
    (old / "_parts").mkdir(parents=True)
    (new / "_parts_supplement").mkdir(parents=True)
    fields = ["member", "npy", "message", "split", "label", "category", "match"]
    for d, name, row in (
        (old / "_parts", "a.csv", dict(member="A/1. X/a.MOV", npy="o1.npy", message="", split="train", label="X", category="A", match="")),
        (new / "_parts_supplement", "b.csv", dict(member="A/2. Y/b.MP4", npy="s1.npy", message="", split="test", label="Y", category="A", match="stem")),
    ):
        with (d / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerow(row)
    (old / "dataset_info.json").write_text(json.dumps({"name": "n", "language": "ISL", "license": "l", "source_url": "u"}))
    before = sorted(p.name for p in old.rglob("*"))
    assert build_manifest(old, new) == 2
    rows = list(csv.DictReader((new / "manifest.csv").open()))
    assert [r["path"] for r in rows] == ["../include/o1.npy", "s1.npy"] and not (old / "manifest.csv").exists()
    assert sorted(p.name for p in old.rglob("*")) == before
    assert "unverified" in json.loads((new / "dataset_info.json").read_text())["notes"]


def test_build_manifest_uses_path_label_not_nested_extra_folder(tmp_path) -> None:
    old, new = tmp_path / "include", tmp_path / "include_v2"
    (old / "_parts").mkdir(parents=True)
    (new / "_parts_supplement").mkdir(parents=True)
    fields = ["member", "npy", "message", "split", "label", "category"]
    with (old / "_parts" / "a.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow(dict(member="Animals/4. Bird/Extra/x.MOV", npy="o1.npy", message="", split="train", label="Extra", category="Animals"))
    (old / "dataset_info.json").write_text(json.dumps({"name": "n", "language": "ISL", "license": "l", "source_url": "u"}))
    build_manifest(old, new)
    assert [r["label"] for r in csv.DictReader((new / "manifest.csv").open())] == ["Bird"]
