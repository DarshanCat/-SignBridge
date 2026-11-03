"""Charts for the project report, drawn only from docs/evaluation, plus the landmark skeleton figure drawn from stored FEATURES (numbers, no video frames).

    python paper/report/make_charts.py

Output: paper/report/figures/chart_*.png and skeleton_sign.png. The browser-versus-offline, y scale and framing charts are the paper's figures
converted to PNG (run paper/figures/make_figures.py first, and keep the MiKTeX pdftoppm path below).
"""
import csv
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
EV = ROOT / "docs" / "evaluation"
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 9.5})
BLUE, RED, GREEN, GREY, AMBER = "#1f5fa8", "#c0392b", "#2e8b57", "#7f8c8d", "#d4a017"
ARCH = [("cnn", "1D CNN"), ("bigru", "BiGRU"), ("transformer", "Transformer")]
PDFTOPPM = Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64/miktex-pdftoppm.exe"


def model_comparison():
    m = json.load(open(EV / "seed0_model_metrics.json"))
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    metrics = [("top1_accuracy", "Top-1", BLUE), ("top5_accuracy", "Top-5", GREEN), ("macro_f1", "Macro F1", AMBER)]
    for i, (k, lab, c) in enumerate(metrics):
        vals = [m[f"baseline_{a}"]["test"][k] for a, _ in ARCH]
        xs = np.arange(len(ARCH)) + (i - 1) * 0.26
        ax.bar(xs, vals, 0.25, color=c, label=lab)
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.01, f"{v:.3f}", ha="center", fontsize=7)
    ax.set_xticks(range(len(ARCH)))
    ax.set_xticklabels([n for _, n in ARCH])
    ax.set_ylim(0.5, 1.07)
    ax.set_ylabel("test split (816 samples)")
    ax.legend(ncol=3, frameon=False, loc="upper center")
    fig.tight_layout()
    fig.savefig(OUT / "chart_model_comparison.png", dpi=200)
    plt.close(fig)


def confusion():
    rows = list(csv.reader(open(EV / "confusion_matrix_cnn.csv", encoding="utf-8")))
    classes = rows[0][1:]
    cm = np.array([[int(v) for v in r[1:]] for r in rows[1:]])
    off = cm.copy()
    np.fill_diagonal(off, 0)
    pairs = sorted(((off[i, j], classes[i], classes[j]) for i in range(len(classes)) for j in range(len(classes)) if off[i, j]), reverse=True)[:12]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    labels = [f"{a}  →  {b}" for _, a, b in pairs][::-1]
    ax.barh(range(len(pairs)), [n for n, _, _ in pairs][::-1], color=RED)
    ax.set_yticks(range(len(pairs)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("test samples of the true class predicted as the other class")
    ax.set_title("Most frequent confusions of the 1D CNN (test split)")
    fig.tight_layout()
    fig.savefig(OUT / "chart_confusions_top_pairs.png", dpi=200)
    plt.close(fig)
    # heat map of the classes with the most errors
    errs = off.sum(axis=1) + off.sum(axis=0)
    top = np.argsort(-errs)[:14]
    sub = cm[np.ix_(top, top)]
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    im = ax.imshow(sub, cmap="Blues")
    names = [classes[i] for i in top]
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=7.5)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(names, fontsize=7.5)
    for i in range(len(top)):
        for j in range(len(top)):
            if sub[i, j]:
                ax.text(j, i, str(sub[i, j]), ha="center", va="center", fontsize=7, color="white" if sub[i, j] > sub.max() * 0.55 else "black")
    ax.set_xlabel("predicted class")
    ax.set_ylabel("true class")
    ax.set_title("Confusion matrix of the 14 classes with the most errors (1D CNN, test split)")
    fig.tight_layout()
    fig.savefig(OUT / "chart_confusion_heatmap.png", dpi=200)
    plt.close(fig)


def threshold_curves():
    m = json.load(open(EV / "seed0_model_metrics.json"))
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.0))
    for (a, name), c in zip(ARCH, (BLUE, GREEN, AMBER)):
        curve = m[f"baseline_{a}"]["test"]["accuracy_vs_coverage"]
        th = [x["threshold"] for x in curve]
        cov = [x["coverage"] for x in curve]
        acc = [x["accuracy_on_answered"] for x in curve]
        axes[0].plot(cov, acc, "-o", ms=3, color=c, label=name)
        axes[1].plot(th, cov, "-o", ms=3, color=c, label=name)
        for t, cv, ac in zip(th, cov, acc):
            if abs(t - 0.7) < 1e-9:
                axes[0].annotate("0.7", (cv, ac), textcoords="offset points", xytext=(4, -9), fontsize=7, color=c)
    axes[0].set_xlabel("coverage (share of samples answered)")
    axes[0].set_ylabel("accuracy on answered samples")
    axes[0].legend(frameon=False, fontsize=7.5)
    axes[1].set_xlabel("confidence threshold")
    axes[1].set_ylabel("coverage")
    fig.suptitle("Accuracy against coverage, test split", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(OUT / "chart_threshold_curves.png", dpi=200)
    plt.close(fig)


def segmentation():
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.0), sharey=True)
    for ax, split in zip(axes, ("val", "test")):
        d = json.load(open(EV / f"segmentation_{split}.json"))["results"]
        gaps = [("gap0", "natural\nmargins"), ("gap10", "10 rest\nframes"), ("gap20", "20 rest\nframes")]
        series = [("split_correct", "split correctly", BLUE), ("recognized_correct", "recognized correctly", GREEN), ("recognized_wrong", "accepted but wrong", RED), ("unrecognized", "UNRECOGNIZED", GREY)]
        for i, (k, lab, c) in enumerate(series):
            vals = [d[g][k] / d[g]["true_signs"] for g, _ in gaps]
            xs = np.arange(len(gaps)) + (i - 1.5) * 0.2
            ax.bar(xs, vals, 0.19, color=c, label=lab if split == "val" else None)
        ax.set_xticks(range(len(gaps)))
        ax.set_xticklabels([n for _, n in gaps], fontsize=7.5)
        ax.set_title(f"{split} streams ({d['gap0']['true_signs']} signs)")
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("share of real signs")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=7.5, loc="lower center", ncol=4)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT / "chart_segmentation.png", dpi=200)
    plt.close(fig)


def paper_figures_to_png():
    for name in ("fig_browser_vs_offline", "fig_yscale", "fig_framing"):
        pdf = ROOT / "paper" / "figures" / f"{name}.pdf"
        subprocess.run([str(PDFTOPPM), "-r", "220", "-png", "-singlefile", str(pdf), str(OUT / name.replace("fig_", "chart_"))], check=True, capture_output=True)


# ---------------------------------------------------------------- skeleton from features
POSE_LINES = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28)]
HAND_LINES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]


def skeleton(label_wanted="Hello"):
    rows = list(csv.DictReader(open(ROOT / "data/processed/include_v2/manifest.csv", encoding="utf-8")))
    pick = next(r for r in rows if r["split"] == "test" and r["label"].lower() == label_wanted.lower())
    x = np.load((ROOT / "data/processed/include_v2" / pick["path"]).resolve())
    t = x.shape[0]
    idx = np.linspace(0, t - 1, 8).round().astype(int)
    fig, axes = plt.subplots(2, 4, figsize=(6.8, 4.6))
    for ax, i in zip(axes.ravel(), idx):
        f = x[i].reshape(-1, 3)
        pose, lh, rh = f[:33], f[33:54], f[54:75]
        for a, b in POSE_LINES:
            ax.plot([pose[a, 0], pose[b, 0]], [-pose[a, 1], -pose[b, 1]], "-", color="#334155", lw=1.4)
        ax.plot(pose[0, 0], -pose[0, 1], "o", color="#334155", ms=11, mfc="none")  # head marker at the nose, not a face
        for hand, col in ((lh, GREEN), (rh, RED)):
            if np.abs(hand).sum() == 0:
                continue
            for a, b in HAND_LINES:
                ax.plot([hand[a, 0], hand[b, 0]], [-hand[a, 1], -hand[b, 1]], "-", color=col, lw=1.0)
            ax.plot(hand[:, 0], -hand[:, 1], ".", color=col, ms=2.5)
        ax.set_xlim(-2.6, 2.6)
        ax.set_ylim(-3.6, 1.6)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"frame {i + 1} of {t}", fontsize=7.5)
    fig.suptitle(f"One INCLUDE test sample of the sign '{pick['label']}', drawn from the 225 stored features (no video)", fontsize=9)
    fig.text(0.5, 0.01, "Coordinates: shoulder midpoint at the origin, unit = shoulder width. Left hand green, right hand red.", ha="center", fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(OUT / "skeleton_sign.png", dpi=200)
    plt.close(fig)
    return pick["label"], pick["path"]


if __name__ == "__main__":
    model_comparison()
    confusion()
    threshold_curves()
    segmentation()
    paper_figures_to_png()
    print("skeleton:", skeleton())
    print("charts written to", OUT)
