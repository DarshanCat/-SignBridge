# Does a lower frame rate cost accuracy? (validation only)

Authors' predefined split, signer independence not verified. The 347 validation sequences of INCLUDE v2, the three baseline 1D CNNs (seeds 0, 1, 2, no face, `data/models_v2`, `data/models_seeds`), no retraining, **the test split was never read**. The 12.5 fps row reproduces each model's recorded validation macro-F1 exactly (a check that the evaluation is the training one).

Training rate: INCLUDE videos are 25 fps (30 videos sampled from the archives on disk, all 25.0) and the features keep every second frame, so **12.5 frames per second**. Live rate: **6.7 frames per second**, the sustained landmark extraction rate of the browser measured in `LATENCY.md` (CPU delegate); 8 is the rate with the GPU delegate requested, added as an extra row. A lower rate is simulated by keeping, from each validation sequence, the frames nearest to the times k / rate; the model's own preprocessing (gap fill, resample to 32 frames) then runs. Three sampling phases are averaged. A sequence has a median of 32 frames at 12.5 fps, 21 at 8 fps and 17 at 6.7 fps before the resampling to 32.

## CNN validation macro-F1

| Frame rate | Seed 0 | Seed 1 | Seed 2 | Mean ± SD | Difference from 12.5 fps (95% interval over the 3 seeds) |
|---|---|---|---|---|---|
| 12.5 (training rate) | 0.9039 | 0.9123 | 0.9217 | 0.9127 ± 0.0089 | reference |
| 8.0 (GPU delegate, extra) | 0.8597 | 0.8801 | 0.8977 | 0.8792 ± 0.0190 | -0.0335 (-0.0589 to -0.0081) |
| 6.7 (live, CPU delegate) | 0.8660 | 0.8789 | 0.8989 | 0.8812 ± 0.0166 | -0.0314 (-0.0508 to -0.0121) |

Top-1 accuracy: 12.5 fps 0.9193, 0.9308, 0.9366; 8.0 fps 0.8886, 0.9059, 0.9232; 6.7 fps 0.8915, 0.9059, 0.9203 (seeds 0, 1, 2).

Spread over the three sampling phases (macro-F1, lowest to highest) at 6.7 fps: seed 0 0.8599 to 0.8698; seed 1 0.8625 to 0.8967; seed 2 0.8843 to 0.9191.

## Reading

- At the live rate the CNN loses about 3.1 points of validation macro-F1 on average; every seed drops (per seed: -3.8, -3.3, -2.3 points). The interval over three seeds excludes zero.
- The 8 fps row is about as low as the 6.7 fps row, so most of the loss is already there at 8 fps; the small difference between the two is within the noise of one validation set of 347 sequences.
- This is a simulation on stored landmarks: it thins the frames but does not reproduce everything the live path changes (the browser's own tracking and smoothing, uneven timing between frames, a webcam instead of INCLUDE footage, 4:3 framing). It isolates the frame rate only, and it is not a measure of live accuracy.
- A model trained or fine tuned on sequences thinned like this (a temporal augmentation) could probably recover some of the loss; that was not tried (no retraining here).
