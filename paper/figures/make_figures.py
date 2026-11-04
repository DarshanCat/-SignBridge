"""Figures for the paper, drawn only from files in docs/evaluation (no number is typed in here except bin edges read from the markdown tables).

    python paper/figures/make_figures.py        (needs matplotlib; the backend venv has it)

fig_browser_vs_offline.pdf   accuracy and wrong-accepted rate, offline against the browser path (test videos, CNN, n = 100)
fig_yscale.pdf               accuracy against a y scale error, browser 16:9 and 4:3 (validation videos, CNN)
fig_pipeline.pdf             compact flow of the browser deployment pipeline (Section IV; no data)
fig_framing.pdf              accuracy against shoulder width as a fraction of the picture width (validation videos shrunk toward the centre, CNN)

Inputs, all in docs/evaluation (the only place this script reads from; nothing comes from a scratch folder):
    browser_path_rows.json               per video rows, 100 test videos, CNN (figure 1)
    browser_path_validation_sweep.json   y scale sweep, 100 validation videos, CNN (figure 2)
    BROWSER_PATH.md                      the framing table (figure 3)
Not used by any figure yet (they feed the pending three-seed tables): eval_val.json, eval_test.json and seed0_model_metrics.json.
"""
import json
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
EVAL = HERE.parents[1] / "docs" / "evaluation"
for _name in ("browser_path_rows.json", "browser_path_validation_sweep.json", "BROWSER_PATH.md"):
    if not (EVAL / _name).is_file():
        raise SystemExit(f"missing input {EVAL / _name}")
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
W, H = 3.4, 2.05  # inches, one IEEE column
BLUE, RED, GREY, GREEN = "#1f5fa8", "#c0392b", "#7f8c8d", "#2e8b57"


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def browser_vs_offline():
    rows = json.load(open(EVAL / "browser_path_rows.json"))["rows"]
    n = len(rows)
    sources = [("offline", "Offline\nfeatures"), ("br16x9", "Browser\n16:9"), ("br4x3", "Browser 4:3\n(y rescaled)"), ("br4x3_raw", "Browser 4:3\n(no rescale)")]
    acc, wrong, ci = [], [], []
    for key, _ in sources:
        ok = sum(1 for r in rows if r[key]["accepted"] and r[key]["top"].lower() == r["label"].lower())
        bad = sum(1 for r in rows if r[key]["accepted"] and r[key]["top"].lower() != r["label"].lower())
        lo, hi = wilson(ok, n)
        acc.append(ok / n)
        wrong.append(bad / n)
        ci.append((ok / n - lo, hi - ok / n))
    fig, ax = plt.subplots(figsize=(W, H))
    xs = range(len(sources))
    ax.bar([x - 0.2 for x in xs], acc, 0.4, color=BLUE, label="correct and accepted", yerr=list(zip(*ci)), capsize=2, error_kw={"lw": 0.8})
    ax.bar([x + 0.2 for x in xs], wrong, 0.4, color=RED, label="wrong and accepted")
    for x, a, w in zip(xs, acc, wrong):
        ax.text(x - 0.2, a + 0.07, f"{a:.2f}", ha="center", va="bottom", fontsize=6.5)
        ax.text(x + 0.2, w + 0.01, f"{w:.2f}", ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([s[1] for s in sources])
    ax.set_ylim(0, 1.22)
    ax.set_ylabel(f"share of test videos (n = {n})")
    ax.legend(loc="upper center", ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "fig_browser_vs_offline.pdf")
    plt.close(fig)


def yscale():
    d = json.load(open(EVAL / "browser_path_validation_sweep.json"))
    base, sw = d["baseline"], d["sweep"]
    factors = sorted({float(re.match(r"y_x([\d.]+)_on", k).group(1)) for k in sw if k.startswith("y_x")} | {1.0})

    def series(framing, idx):
        out = []
        for f in factors:
            out.append(base["br16x9" if framing == "16x9" else "br4x3"][idx] if f == 1.0 else sw[f"y_x{f}_on_{framing}"][idx])
        return out

    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(factors, series("16x9", 0), "-o", color=BLUE, ms=3, lw=1.2, label="accuracy, 16:9")
    ax.plot(factors, series("4x3", 0), "-s", color=GREEN, ms=3, lw=1.2, label="accuracy, 4:3")
    ax.plot(factors, series("16x9", 1), "--o", color=RED, ms=3, lw=1.0, label="wrong accepted, 16:9", mfc="none")
    ax.axvline(1.0, color=GREY, lw=0.6, ls=":")
    ax.axvspan(0.85, 1.20, color=GREY, alpha=0.12, lw=0)
    ax.text(1.025, 0.9, "augmentation\nrange", fontsize=6.5, color=GREY, va="top")
    ax.set_xlabel("y scale error factor (1.0 is the exact rescale)")
    ax.set_ylabel("share of validation videos")
    ax.set_ylim(0, 1.0)
    ax.legend(loc="center right", frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "fig_yscale.pdf")
    plt.close(fig)


def framing():
    text = (EVAL / "BROWSER_PATH.md").read_text(encoding="utf-8")
    sec = text.split("## Framing: how small can the signer be")[1].split("At 30 percent size")[0]
    rows = re.findall(r"\|\s*([\d.]+) to ([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)\s*\|", sec)
    mids = [(float(a) + float(b)) / 2 for a, b, *_ in rows]
    acc = [float(r[2]) for r in rows]
    wrong = [float(r[3]) for r in rows]
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(mids, acc, "-o", color=BLUE, ms=3, lw=1.2, label="accuracy")
    ax.plot(mids, wrong, "--o", color=RED, ms=3, lw=1.0, mfc="none", label="wrong accepted")
    ax.axvline(0.10, color=GREY, lw=0.8, ls=":")
    ax.text(0.103, 0.12, "warning\nthreshold 0.10", fontsize=6.5, color=GREY)
    ax.axvspan(0.116, 0.149, color=GREY, alpha=0.12, lw=0)
    ax.text(0.1205, 0.96, "INCLUDE\nsigners", fontsize=6.5, color=GREY, va="top")
    ax.set_xlabel("shoulder width (fraction of picture width)")
    ax.set_ylabel("share of validation videos")
    ax.set_ylim(0, 1.0)
    ax.legend(loc="center left", frameon=False)
    fig.tight_layout()
    fig.savefig(HERE / "fig_framing.pdf")
    plt.close(fig)


def pipeline():
    """Compact flow of Section IV: what runs in the browser and what runs on the server."""
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(W, 1.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.2)
    ax.axis("off")

    def box(x, y, w, h, text, fc, ec):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15", fc=fc, ec=ec, lw=0.8))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=6.3, linespacing=1.15)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops={"arrowstyle": "-|>", "lw": 0.8, "color": "#444444", "shrinkA": 0, "shrinkB": 0, "mutation_scale": 7})

    ax.text(0.0, 6.0, "browser", fontsize=6.5, color=BLUE, weight="bold", va="center")
    ax.text(0.0, 2.75, "server", fontsize=6.5, color=GREY, weight="bold", va="center")
    ytop, ybot, h = 3.95, 0.45, 1.5
    w = 2.9
    xs = [0.0, 3.55, 7.1]
    box(xs[0], ytop, w, h, "camera picture\n(1280\u00d7720 asked;\nany shape kept)", "#e8f0fa", BLUE)
    box(xs[1], ytop, w, h, "MediaPipe Holistic\n75 landmarks\n(pose, both hands)", "#e8f0fa", BLUE)
    box(xs[2], ytop, w, h, "y′ = y·(16/9)/(w/h)\nlandmark buffer\n(≤60 frames)", "#e8f0fa", BLUE)
    arrow(xs[0] + w, ytop + h / 2, xs[1], ytop + h / 2)
    arrow(xs[1] + w, ytop + h / 2, xs[2], ytop + h / 2)
    arrow(xs[2] + w / 2, ytop, xs[2] + w / 2, ybot + h)
    ax.text(xs[2] + w / 2 - 0.12, 3.2, "landmarks only\n(no video)", fontsize=5.8, color="#444444", va="center", ha="right")
    box(xs[2], ybot, w, h, "shoulder-width\nnormalization,\nresample to 32", "#f1f1f1", GREY)
    box(xs[1], ybot, w, h, "1D CNN\nsoftmax, top-1", "#f1f1f1", GREY)
    box(xs[0], ybot, w, h, "confidence ≥ 0.7?\nlabel or\nUNRECOGNIZED", "#f1f1f1", GREY)
    arrow(xs[2], ybot + h / 2, xs[1] + w, ybot + h / 2)
    arrow(xs[1], ybot + h / 2, xs[0] + w, ybot + h / 2)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.savefig(HERE / "fig_pipeline.pdf")
    plt.close(fig)


if __name__ == "__main__":
    browser_vs_offline()
    yscale()
    framing()
    pipeline()
    print("figures written to", HERE)
