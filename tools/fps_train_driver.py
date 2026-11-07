"""Train the CNN with frame rate augmentation (--fps-augment 6 12.5), seeds 0, 1, 2, the same settings as the three-seed baseline (epochs_max 60, patience 10, max_gap 3,
batch 16, lr 0.001, seq_len 32, hidden 128, no other augmentation). Validation only (--no-test). One lane per seed, checkpointed and resumable.
usage (repository root): backend\.venv\Scripts\python tools\fps_train_driver.py --seed 0 --threads 5   (quote paths that contain spaces when launching)"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "models_fps"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--threads", type=int, default=5)
    a = p.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    d = OUT / f"s{a.seed}" / "cnn"
    log = OUT / f"driver_s{a.seed}.log"
    if (d / "metrics.json").is_file():
        log.open("a").write(f"{time.strftime('%H:%M:%S')} done already\n")
        return 0
    resume = (d / "checkpoint_last.pt").is_file()
    cmd = [sys.executable, "-u", "-m", "training.train", "--manifest", str(ROOT / "data" / "processed" / "include_v2" / "manifest.csv"), "--out", str(d), "--arch", "cnn",
           "--seed", str(a.seed), "--epochs", "60", "--patience", "10", "--max-gap", "3", "--threads", str(a.threads), "--fps-augment", "6", "12.5", "--no-test", "--checkpoint"] + (["--resume"] if resume else [])
    log.open("a").write(f"{time.strftime('%H:%M:%S')} start {'resume' if resume else 'fresh'}\n")
    with (OUT / f"s{a.seed}_cnn.train.log").open("a", encoding="utf-8") as lf:
        rc = subprocess.run(cmd, cwd=ROOT / "backend", stdout=lf, stderr=subprocess.STDOUT).returncode
    log.open("a").write(f"{time.strftime('%H:%M:%S')} end rc {rc}\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
