import json

import pytest

from tests.test_training_pipeline import make_dataset
from training.dataset import load_splits
from training.pilot import LABEL, main, parse_run
from training.train import train


def test_parse_run() -> None:
    assert parse_run("a:bigru") == ("a", "bigru", {})
    assert parse_run("a:cnn1d:epochs=3,lr=0.01,augment=true") == ("a", "cnn1d", {"epochs": 3, "lr": 0.01, "augment": True})
    for bad in ["x", ":bigru", "a:bigru:nope=1"]:
        with pytest.raises(ValueError):
            parse_run(bad)


def test_pilot_never_reads_the_test_split(tmp_path) -> None:
    m = make_dataset(tmp_path)
    for s in load_splits(m).samples["test"]:
        s.path.write_bytes(b"not a numpy file")  # if any test file were opened the run would fail
    rep = train(m, tmp_path / "out", arch="bigru", epochs=1, hidden=8, layers=1, seq_len=12, num_threads=1, evaluate_test=False)
    assert "test" not in rep["results"] and "val" in rep["results"]


def test_pilot_cli_labels_results_and_refuses_to_overwrite(tmp_path, monkeypatch) -> None:
    m = make_dataset(tmp_path)
    out, models = tmp_path / "pilot", tmp_path / "models"
    args = ["pilot", "--manifest", str(m), "--out", str(out), "--models-dir", str(models), "--threads", "1", "--runs", "t1:bigru:epochs=1,hidden=8,layers=1,seq_len=12"]
    monkeypatch.setattr("sys.argv", args)
    assert main() == 0
    r = json.loads((out / "t1.json").read_text())
    assert r["label"] == LABEL == "pilot, v1 partial split, not reportable"
    assert r["test_split_evaluated"] is False and "test" not in r["sample_counts"]
    monkeypatch.setattr("sys.argv", args)
    assert main() == 2  # existing result is not overwritten
