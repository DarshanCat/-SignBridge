"""docs/evaluation/FPS_EFFECT.md from fps_effect.json. usage (repository root): python -I tools/fps_effect/report.py"""
import json
import statistics as st
from pathlib import Path

EV = Path(__file__).resolve().parents[2] / "docs" / "evaluation"
d = json.loads((EV / "fps_effect.json").read_text(encoding="utf-8"))
ps, diff = d["per_seed"], d["difference_vs_training_rate"]
rates = [str(r) for r in d["rates"]]
ms = lambda xs: f"{st.mean(xs):.4f} ± {st.stdev(xs):.4f}"
o = []
P = o.append
P("# Does a lower frame rate cost accuracy? (validation only)\n")
P("Authors' predefined split, signer independence not verified. The 347 validation sequences of INCLUDE v2, the three baseline 1D CNNs (seeds 0, 1, 2, no face, `data/models_v2`, `data/models_seeds`), "
  "no retraining, **the test split was never read**. The 12.5 fps row reproduces each model's recorded validation macro-F1 exactly (a check that the evaluation is the training one).\n")
P("Training rate: INCLUDE videos are 25 fps (30 videos sampled from the archives on disk, all 25.0) and the features keep every second frame, so **12.5 frames per second**. "
  "Live rate: **6.7 frames per second**, the sustained landmark extraction rate of the browser measured in `LATENCY.md` (CPU delegate); 8 is the rate with the GPU delegate requested, added as an extra row. "
  "A lower rate is simulated by keeping, from each validation sequence, the frames nearest to the times k / rate; the model's own preprocessing (gap fill, resample to 32 frames) then runs. "
  f"Three sampling phases are averaged. A sequence has a median of {ps['0']['12.5']['median_frames_kept']} frames at 12.5 fps, {ps['0']['8.0']['median_frames_kept']} at 8 fps and {ps['0']['6.7']['median_frames_kept']} at 6.7 fps before the resampling to 32.\n")
P("## CNN validation macro-F1\n")
P("| Frame rate | Seed 0 | Seed 1 | Seed 2 | Mean ± SD | Difference from 12.5 fps (95% interval over the 3 seeds) |")
P("|---|---|---|---|---|---|")
for r in rates:
    vals = [ps[s][r]["macro_f1"] for s in ("0", "1", "2")]
    label = {"12.5": "12.5 (training rate)", "8.0": "8.0 (GPU delegate, extra)", "6.7": "6.7 (live, CPU delegate)"}[r]
    if r == "12.5":
        P(f"| {label} | " + " | ".join(f"{v:.4f}" for v in vals) + f" | {ms(vals)} | reference |")
    else:
        x = diff[r]
        P(f"| {label} | " + " | ".join(f"{v:.4f}" for v in vals) + f" | {ms(vals)} | {x['mean_difference']:+.4f} ({x['lo']:+.4f} to {x['hi']:+.4f}){'' if x['clear'] else ', no clear change'} |")
P("\nTop-1 accuracy: " + "; ".join(f"{r} fps " + ", ".join(f"{ps[s][r]['top1']:.4f}" for s in ('0', '1', '2')) for r in rates) + " (seeds 0, 1, 2).")
P("\nSpread over the three sampling phases (macro-F1, lowest to highest) at 6.7 fps: " + "; ".join(f"seed {s} {min(ps[s]['6.7']['macro_f1_by_phase']):.4f} to {max(ps[s]['6.7']['macro_f1_by_phase']):.4f}" for s in ("0", "1", "2")) + ".\n")
P("## Reading\n")
P(f"- At the live rate the CNN loses about {-diff['6.7']['mean_difference'] * 100:.1f} points of validation macro-F1 on average; every seed drops (per seed: " + ", ".join(f"{x * 100:+.1f}" for x in diff['6.7']['per_seed_difference']) + " points). "
  f"{'The interval over three seeds excludes zero.' if diff['6.7']['clear'] else 'The interval over three seeds contains zero, so with three seeds the drop is not statistically clear, although all three seeds point the same way.'}")
P("- The 8 fps row is about as low as the 6.7 fps row, so most of the loss is already there at 8 fps; the small difference between the two is within the noise of one validation set of 347 sequences.")
P("- This is a simulation on stored landmarks: it thins the frames but does not reproduce everything the live path changes (the browser's own tracking and smoothing, uneven timing between frames, a webcam instead of INCLUDE footage, 4:3 framing). It isolates the frame rate only, and it is not a measure of live accuracy.")
P("- A model trained or fine tuned on sequences thinned like this (a temporal augmentation) could probably recover some of the loss; that was not tried (no retraining here).")
(EV / "FPS_EFFECT.md").write_text("\n".join(o) + "\n", encoding="utf-8", newline="\n")
print("\n".join(o))
