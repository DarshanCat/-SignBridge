# Frame rate augmentation for the CNN (validation only)

Authors' predefined split, signer independence not verified. INCLUDE v2, 347 validation sequences. **The test split was never read**; no model here is a final model. Baseline: the three-seed CNNs without augmentation (`data/models_v2`, `data/models_seeds`). Augmented: the same CNN with the same settings and seeds (epochs_max 60, patience 10, max_gap 3, batch 16, lr 0.001, seq_len 32, hidden 128, no other augmentation) trained with `--fps-augment 6 12.5`: every training sequence is thinned, on every pass, to a rate drawn uniformly between 6 and 12.5 frames per second with a random sampling phase (`training/augment.py`, off by default so old runs are unchanged). Evaluation thins the validation sequences to each rate with the same function, three sampling phases averaged; the 12.5 row is the plain validation score. Epochs run, baseline then augmented: seed 0: 46 then 60; seed 1: 51 then 50; seed 2: 60 then 48.

## Validation macro-F1

| Frame rate | Model | Seed 0 | Seed 1 | Seed 2 | Mean ± SD | Augmented minus baseline (95% interval over the 3 seeds) |
|---|---|---|---|---|---|---|
| 12.5 (training rate) | baseline | 0.9039 | 0.9123 | 0.9217 | 0.9127 ± 0.0089 | |
| | augmented | 0.9211 | 0.9111 | 0.9127 | 0.9150 ± 0.0054 | +0.0023 (-0.0310 to +0.0357), no clear change |
| 8.0 (GPU delegate rate) | baseline | 0.8597 | 0.8801 | 0.8977 | 0.8792 ± 0.0190 | |
| | augmented | 0.9112 | 0.9001 | 0.8900 | 0.9004 ± 0.0106 | +0.0213 (-0.0525 to +0.0950), no clear change |
| 6.7 (live, CPU delegate) | baseline | 0.8660 | 0.8789 | 0.8989 | 0.8812 ± 0.0166 | |
| | augmented | 0.9109 | 0.8957 | 0.8800 | 0.8955 ± 0.0154 | +0.0143 (-0.0651 to +0.0937), no clear change |

Top-1 accuracy (seeds 0, 1, 2): 12.5 fps baseline 0.9193, 0.9308, 0.9366 / augmented 0.9366, 0.9308, 0.9280; 8.0 fps baseline 0.8886, 0.9059, 0.9232 / augmented 0.9289, 0.9203, 0.9145; 6.7 fps baseline 0.8915, 0.9059, 0.9203 / augmented 0.9270, 0.9164, 0.9059.

## Reading

- At the live rate (6.7 fps) augmentation changes validation macro-F1 by +1.4 points on average (per seed +4.5, +1.7, -1.9); the interval over three seeds contains zero.
- At the training rate (12.5 fps) the change is +0.2 points (per seed +1.7, -0.1, -0.9), which contains zero.
- Validation only, three seeds, one validation set of 347 sequences shared by all models: the intervals show seed to seed variation, not sampling noise of the validation set. Nothing here is a statement about live accuracy (see `FPS_EFFECT.md` for what the simulation leaves out). Whether to adopt the augmentation is a decision on these validation numbers; a model trained with it would still need its single test evaluation if it became the final model, and that was not done.
