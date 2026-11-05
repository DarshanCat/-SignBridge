"""Train the face arm of the face comparison: 1D CNN, BiGRU and Transformer with the face block, seeds 0, 1, 2, the same settings as the three-seed baseline
(epochs_max 60, patience 10, max_gap 3, batch 16, lr 0.001, seq_len 32, hidden 128, no augmentation). Validation only: the test split is not read
(--no-test); test numbers are produced afterwards, once per model, by tools/face_report.py.
usage (repository root, detached, one lane per seed):
    backend\\.venv\\Scripts\\python tools\\face_train_driver.py --seed 0 --threads 5
Checkpointed and resumable: a model with metrics.json is skipped, one with checkpoint_last.pt resumes. Log: data/models_face/driver_s<seed>.log"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = ROOT / "data" / "models_face"
ARCHS = ["cnn", "transformer", "bigru"]  # the fast ones first


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--threads", type=int, default=5)
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / f"driver_s{a.seed}.log"

    def say(msg: str) -> None:
        with log.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

    for arch in ARCHS:
        d = OUT / f"s{a.seed}" / arch
        if (d / "metrics.json").is_file():
            say(f"skip {arch} (done)")
            continue
        resume = (d / "checkpoint_last.pt").is_file()
        cmd = [
            sys.executable, "-u", "-m", "training.train", "--manifest", str(ROOT / "data" / "processed" / "include_v2" / "manifest.csv"), "--out", str(d),
            "--arch", arch, "--seed", str(a.seed), "--epochs", "60", "--patience", "10", "--max-gap", "3", "--threads", str(a.threads),
            "--face-dir", str(ROOT / "data" / "processed" / "face_v1"), "--no-test", "--checkpoint",
        ] + (["--resume"] if resume else [])
        say(f"start {arch} {'resume' if resume else 'fresh'}")
        with (OUT / f"s{a.seed}_{arch}.train.log").open("a", encoding="utf-8") as lf:
            rc = subprocess.run(cmd, cwd=BACKEND, stdout=lf, stderr=subprocess.STDOUT).returncode
        say(f"end {arch} rc {rc}")
        if rc != 0:
            return rc
    say("all done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
