"""docs/evaluation/FPS_AUGMENT.md from fps_augment_results.json. usage (repository root): python -I tools/fps_effect/compare_augment_report.py"""
import json
import statistics as st
from pathlib import Path

EV = Path(__file__).resolve().parents[2] / "docs" / "evaluation"
d = json.loads((EV / "fps_augment_results.json").read_text(encoding="utf-8"))
b, a, diff = d["baseline"], d["fps_augment"], d["difference"]
rates = [str(r) for r in d["rates"]]
ms = lambda xs: f"{st.mean(xs):.4f} ± {st.stdev(xs):.4f}"
name = {"12.5": "12.5 (training rate)", "8.0": "8.0 (GPU delegate rate)", "6.7": "6.7 (live, CPU delegate)"}
o = []
P = o.append
P("# Frame rate augmentation for the CNN (validation only)\n")
P("Authors' predefined split, signer independence not verified. INCLUDE v2, 347 validation sequences. **The test split was never read**; no model here is a final model. "
  "Baseline: the three-seed CNNs without augmentation (`data/models_v2`, `data/models_seeds`). Augmented: the same CNN with the same settings and seeds (epochs_max 60, patience 10, max_gap 3, batch 16, lr 0.001, seq_len 32, hidden 128, "
  "no other augmentation) trained with `--fps-augment 6 12.5`: every training sequence is thinned, on every pass, to a rate drawn uniformly between 6 and 12.5 frames per second with a random sampling phase "
  "(`training/augment.py`, off by default so old runs are unchanged). Evaluation thins the validation sequences to each rate with the same function, three sampling phases averaged; the 12.5 row is the plain validation score. "
  f"Epochs run, baseline then augmented: " + "; ".join(f"seed {s}: {b[s]['epochs_run']} then {a[s]['epochs_run']}" for s in ("0", "1", "2")) + ".\n")
P("## Validation macro-F1\n")
P("| Frame rate | Model | Seed 0 | Seed 1 | Seed 2 | Mean ± SD | Augmented minus baseline (95% interval over the 3 seeds) |")
P("|---|---|---|---|---|---|---|")
for r in rates:
    bv = [b[s][r]["macro_f1"] for s in "012"]
    av = [a[s][r]["macro_f1"] for s in "012"]
    x = diff[r]
    P(f"| {name[r]} | baseline | " + " | ".join(f"{v:.4f}" for v in bv) + f" | {ms(bv)} | |")
    P(f"| | augmented | " + " | ".join(f"{v:.4f}" for v in av) + f" | {ms(av)} | {x['mean']:+.4f} ({x['lo']:+.4f} to {x['hi']:+.4f}){'' if x['clear'] else ', no clear change'} |")
P("\nTop-1 accuracy (seeds 0, 1, 2): " + "; ".join(f"{name[r].split(' ')[0]} fps baseline " + ", ".join(f"{b[s][r]['top1']:.4f}" for s in '012') + " / augmented " + ", ".join(f"{a[s][r]['top1']:.4f}" for s in '012') for r in rates) + ".\n")
P("## Reading\n")
g67, g125 = diff["6.7"], diff["12.5"]
P(f"- At the live rate (6.7 fps) augmentation changes validation macro-F1 by {g67['mean'] * 100:+.1f} points on average (per seed " + ", ".join(f"{x * 100:+.1f}" for x in g67["per_seed"]) + f"); "
  + ("the interval over three seeds excludes zero." if g67["clear"] else "the interval over three seeds contains zero."))
P(f"- At the training rate (12.5 fps) the change is {g125['mean'] * 100:+.1f} points (per seed " + ", ".join(f"{x * 100:+.1f}" for x in g125["per_seed"]) + "), " + ("which excludes zero." if g125["clear"] else "which contains zero.") )
P("- Validation only, three seeds, one validation set of 347 sequences shared by all models: the intervals show seed to seed variation, not sampling noise of the validation set. Nothing here is a statement about live accuracy (see `FPS_EFFECT.md` for what the simulation leaves out). "
  "Whether to adopt the augmentation is a decision on these validation numbers; a model trained with it would still need its single test evaluation if it became the final model, and that was not done.")
(EV / "FPS_AUGMENT.md").write_text("\n".join(o) + "\n", encoding="utf-8", newline="\n")
print("\n".join(o))
