"""Architecture diagram, the two pipeline flowcharts, the gloss hub and the training data pipeline for the project report.

Drawn with matplotlib (Graphviz and Mermaid are not installed here and nothing was downloaded to get them). Output: paper/report/figures/diagram_*.png

    python paper/report/make_diagrams.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

COL = {
    "browser": "#dbeafe", "server": "#dcfce7", "store": "#fef3c7", "ext": "#f1f5f9", "sign": "#e0e7ff", "text": "#fce7f3", "gloss": "#fde68a",
    "edge": "#334155", "arrow": "#475569", "model": "#bbf7d0",
}


def box(ax, x, y, w, h, text, fill, size=8.5, bold=False, edge=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec=edge or COL["edge"], lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, fontweight="bold" if bold else "normal", wrap=True, linespacing=1.25)


def arrow(ax, p, q, text=None, rad=0.0, style="-|>", dy=0.12, dx=0.0, color=None, ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=11, lw=1.2, color=color or COL["arrow"], connectionstyle=f"arc3,rad={rad}", linestyle=ls))
    if text:
        ax.text((p[0] + q[0]) / 2 + dx, (p[1] + q[1]) / 2 + dy, text, ha="center", va="bottom", fontsize=7.5, color="#1e293b", style="italic")


def frame(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def group(ax, x, y, w, h, title, fill):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fill, ec="#94a3b8", lw=1.0, alpha=0.55))
    ax.text(x + 0.12, y + h - 0.12, title, ha="left", va="top", fontsize=9.5, fontweight="bold", color="#0f172a")


def architecture():
    fig, ax = frame(10.2, 6.6)
    group(ax, 0.1, 2.3, 4.4, 4.2, "Browser (Next.js 16, React 19, TypeScript)", COL["browser"])
    box(ax, 0.3, 5.1, 1.9, 0.7, "Webcam\n(1280x720 requested)", "white")
    box(ax, 2.45, 5.1, 1.9, 0.7, "MediaPipe Holistic\nWASM, CPU, in browser", "white")
    box(ax, 0.3, 3.95, 1.9, 0.75, "Landmark buffer\n(60 frames, reset on loss)\n+ y rescale to 16:9", "white")
    box(ax, 2.45, 3.95, 1.9, 0.75, "Panels: Conversation,\nSign to English, English\nto Sign, Record, Check", "white")
    box(ax, 0.3, 2.5, 1.9, 0.9, "3D avatar\nReact Three Fiber,\nMixamo model, clip player", "white")
    box(ax, 2.45, 2.5, 1.9, 0.9, "Framing guide,\nsize warning,\nfooter notices", "white")
    arrow(ax, (2.2, 5.45), (2.45, 5.45))
    arrow(ax, (3.4, 5.1), (1.5, 4.7), rad=0.15)
    group(ax, 5.4, 2.3, 4.7, 4.2, "Backend (FastAPI, PyTorch CPU, spaCy)", COL["server"])
    box(ax, 5.6, 5.1, 2.0, 0.7, "WebSocket /ws/predict\nREST /api/*", "white")
    box(ax, 7.85, 5.1, 2.1, 0.7, "Normalize (225 features)\nresample to 32 frames", "white")
    box(ax, 5.6, 3.95, 2.0, 0.75, "Segmenter\n(continuous signing)", "white")
    box(ax, 7.85, 3.95, 2.1, 0.75, "1D CNN classifier\n+ confidence threshold 0.7", COL["model"])
    box(ax, 5.6, 2.5, 2.0, 0.9, "Text to gloss (spaCy rules)\nGloss to English (rules)", "white")
    box(ax, 7.85, 2.5, 2.1, 0.9, "Avatar plan and registry\nSign recorder (landmarks only)", "white")
    arrow(ax, (4.35, 4.3), (5.6, 5.3), "landmarks (JSON)", dy=0.18)
    arrow(ax, (7.6, 5.45), (7.85, 5.45))
    arrow(ax, (8.9, 5.1), (8.9, 4.7))
    arrow(ax, (7.85, 4.32), (7.6, 4.32))
    arrow(ax, (5.6, 2.95), (4.35, 2.95), "gloss, English, plan", dy=0.1)
    group(ax, 0.1, 0.15, 10.0, 1.85, "", COL["store"])
    ax.text(0.25, 0.22, "Storage and files (nothing is stored on the server at run time except recorder takes)", fontsize=8.5, fontweight="bold", va="bottom")
    box(ax, 0.35, 0.6, 2.2, 0.95, "frontend/public/avatar\nsigner.glb, mediapipe/\n(git-ignored assets)", "white")
    box(ax, 2.8, 0.6, 2.2, 0.95, "frontend/public/animations\n262 clips (JSON, not\nsigner reviewed)", "white")
    box(ax, 5.25, 0.6, 2.3, 0.95, "backend/models\nisl_model.pt, labels.json,\nthreshold.json", "white")
    box(ax, 7.8, 0.6, 2.1, 0.95, "data/recorded\nown takes (landmarks),\ngit-ignored", "white")
    arrow(ax, (1.45, 1.55), (1.25, 2.5), ls="--")
    arrow(ax, (3.9, 1.55), (1.9, 2.5), rad=0.0, ls="--")
    arrow(ax, (6.4, 1.55), (8.9, 3.95), rad=0.0, ls="--")
    arrow(ax, (8.85, 1.55), (8.9, 2.5), ls="--")
    fig.tight_layout(pad=0.2)
    fig.savefig(OUT / "diagram_architecture.png", dpi=200)
    plt.close(fig)


def sign_to_english():
    fig, ax = frame(10.2, 3.9)
    xs = [0.15, 1.85, 3.55, 5.25, 6.95, 8.65]
    labels = [
        ("Webcam\nvideo stays in\nthe browser", COL["browser"]),
        ("MediaPipe\nHolistic\n75 landmarks", COL["browser"]),
        ("Buffer + y\nrescale (aspect)\nWebSocket", COL["browser"]),
        ("Normalize\nshoulder origin and\nscale: 225 values", COL["server"]),
        ("Resample to\n32 frames, fill\nhand gaps (3)", COL["server"]),
        ("1D CNN\nsoftmax over\n262 classes", COL["model"]),
    ]
    for x, (t, c) in zip(xs, labels):
        box(ax, x, 2.35, 1.5, 1.2, t, c)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, (a + 1.5, 2.95), (b, 2.95))
    box(ax, 8.65, 0.55, 1.5, 1.2, "Confidence\n>= 0.7 ?\nelse UNRECOGNIZED", COL["gloss"])
    box(ax, 6.95, 0.55, 1.5, 1.2, "Class label\nto gloss\n(dictionary)", COL["gloss"])
    box(ax, 5.25, 0.55, 1.5, 1.2, "Gloss\nsequence\n(undo, clear)", COL["gloss"])
    box(ax, 3.55, 0.55, 1.5, 1.2, "Gloss to\nEnglish rules\n(heuristic)", COL["text"])
    box(ax, 1.85, 0.55, 1.5, 1.2, "English\nsentence in\nthe chat", COL["text"])
    arrow(ax, (9.4, 2.35), (9.4, 1.75))
    for a, b in ((8.65, 8.45), (6.95, 6.75), (5.25, 5.05), (3.55, 3.35)):
        arrow(ax, (a, 1.15), (b, 1.15))
    ax.text(5.1, 3.85, "Sign to English pipeline (isolated: one predict per sign; continuous: segmenter, then the same classifier)", ha="center", fontsize=9, fontweight="bold")
    fig.tight_layout(pad=0.2)
    fig.savefig(OUT / "diagram_pipeline_sign_to_english.png", dpi=200)
    plt.close(fig)


def english_to_sign():
    fig, ax = frame(10.2, 3.9)
    xs = [0.15, 1.85, 3.55, 5.25, 6.95, 8.65]
    labels = [
        ("English text\n(typed in the\nchat box)", COL["text"]),
        ("spaCy parse\nlemmas, tenses,\nclauses", COL["server"]),
        ("Gloss rules:\ntime first, SOV,\nNOT, WH last", COL["gloss"]),
        ("Dictionary\n313 glosses,\nfingerspell tag", COL["gloss"]),
        ("Avatar plan:\nwhich glosses\nhave a clip", COL["server"]),
        ("Fetch and\nvalidate clips\n(JSON)", COL["browser"]),
    ]
    for x, (t, c) in zip(xs, labels):
        box(ax, x, 2.35, 1.5, 1.2, t, c)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, (a + 1.5, 2.95), (b, 2.95))
    box(ax, 8.65, 0.55, 1.5, 1.2, "Sequence\nplayer: 0.25 s\neased blends", COL["browser"])
    box(ax, 6.95, 0.55, 1.5, 1.2, "Head markers\nfor negation and\nquestions", COL["browser"])
    box(ax, 5.25, 0.55, 1.5, 1.2, "Pose smoothing,\nidle motion,\nrest hands", COL["browser"])
    box(ax, 3.55, 0.55, 1.5, 1.2, "3D avatar\nrenders the\nsentence", COL["sign"])
    box(ax, 1.85, 0.55, 1.5, 1.2, "Words without\na clip are\nlisted in the chat", COL["text"])
    arrow(ax, (9.4, 2.35), (9.4, 1.75))
    arrow(ax, (8.65, 1.15), (8.45, 1.15))
    arrow(ax, (6.95, 1.15), (6.75, 1.15))
    arrow(ax, (5.25, 1.15), (5.05, 1.15))
    arrow(ax, (3.55, 1.15), (3.35, 1.15))
    ax.text(5.1, 3.85, "English to Sign pipeline (a gloss without a clip is skipped and reported, never faked)", ha="center", fontsize=9, fontweight="bold")
    fig.tight_layout(pad=0.2)
    fig.savefig(OUT / "diagram_pipeline_english_to_sign.png", dpi=200)
    plt.close(fig)


def gloss_hub():
    fig, ax = frame(10.2, 3.6)
    box(ax, 0.2, 1.3, 2.0, 1.0, "English text\n(typed or shown)", COL["text"], bold=True)
    box(ax, 4.0, 1.1, 2.2, 1.4, "GLOSS\nshared representation:\nupper case ISL word tokens", COL["gloss"], size=9.5, bold=True)
    box(ax, 8.0, 2.05, 2.0, 1.0, "Sign recognizer\n(landmarks to class)", COL["model"], bold=True)
    box(ax, 8.0, 0.55, 2.0, 1.0, "3D avatar\n(clips per gloss)", COL["sign"], bold=True)
    arrow(ax, (2.2, 1.95), (4.0, 1.95), "text to gloss (spaCy rules)", dy=0.12)
    arrow(ax, (4.0, 1.45), (2.2, 1.45), "gloss to English (heuristic rules)", dy=-0.38)
    arrow(ax, (8.0, 2.55), (6.2, 2.1), "label to gloss", dy=0.12)
    arrow(ax, (6.2, 1.5), (8.0, 1.05), "gloss to clip", dy=-0.38)
    ax.text(5.1, 3.3, "Gloss is the only thing the two directions share", ha="center", fontsize=9.5, fontweight="bold")
    fig.tight_layout(pad=0.2)
    fig.savefig(OUT / "diagram_gloss_hub.png", dpi=200)
    plt.close(fig)


def data_pipeline():
    fig, ax = frame(10.2, 3.4)
    steps = [
        ("INCLUDE videos\n(zip archives,\nCC BY-NC-SA 4.0)", COL["ext"]),
        ("Python MediaPipe\nHolistic, every\nsecond frame", COL["server"]),
        ("Normalize:\n225 features,\nT x 225 arrays", COL["server"]),
        ("Audit + manifest\n(authors' split:\n3121 / 347 / 816)", COL["store"]),
        ("Train 1D CNN,\nBiGRU, Transformer\n(validation only)", COL["model"]),
        ("Threshold on\nvalidation, test\nonce per model", COL["gloss"]),
    ]
    xs = [0.15, 1.85, 3.55, 5.25, 6.95, 8.65]
    for x, (t, c) in zip(xs, steps):
        box(ax, x, 1.2, 1.5, 1.2, t, c)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(ax, (a + 1.5, 1.8), (b, 1.8))
    ax.text(5.1, 3.0, "Offline data and training pipeline", ha="center", fontsize=9.5, fontweight="bold")
    ax.text(5.1, 0.55, "Retargeting turns one training sample per class into an avatar clip: shoulder and elbow direction, hand orientation and finger curl per frame.", ha="center", fontsize=8, style="italic")
    fig.tight_layout(pad=0.2)
    fig.savefig(OUT / "diagram_data_pipeline.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    for f in (architecture, sign_to_english, english_to_sign, gloss_hub, data_pipeline):
        f()
    print("diagrams written to", OUT)
