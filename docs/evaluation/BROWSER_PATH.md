# Browser path versus offline path

Authors' predefined split, signer independence not verified. 100 videos from the INCLUDE test split (816 samples), one per class, drawn with seed 0 from the test samples whose video is in `zips_keep`. Test videos only; the model was not trained or tuned on them. Not a new test evaluation of the model (the one-time test numbers are in `results.md`); this measures what the browser capture path loses relative to the offline path on a small sample. No clip or sign is signer reviewed.

## What was measured

The same 100 videos were classified from seven landmark sources with the live code path (`process_sequence`, then the 1D CNN and the validation threshold 0.7, with the app's buffer rules: newest 60 frames, buffer dropped after 15 frames without a body pose):

| Source | What it is |
|---|---|
| offline | the stored INCLUDE features, 1080p, every frame (the normal evaluation path) |
| py16x9 | Python MediaPipe on the sampled 1280x720 frames |
| br16x9 | browser MediaPipe (Chrome, the app's own self-hosted MediaPipe files and options) on the same 1280x720 frames |
| py4x3, br4x3 | the same for 4:3 letterboxed 640x480 frames, with y rescaled to 16:9 as the app does now |
| py4x3_raw, br4x3_raw | the same 4:3 landmarks without the rescaling (what the app sent before commit 963119d) |

Isolated mode: one `predict` per video, all sampled frames of that video.

## Method and what it does not cover

- **Frame stepping, not a live fake camera.** Headless Chrome extracts about 6 frames per second, so a looping fake camera drops frames and would mix capture starvation into the error rate. Instead every sampled frame was handed to MediaPipe in order, so none was dropped and no take is excluded for low frame rate. Every 3rd source frame was used (about 8 to 10 frames per second, close to what a live browser achieves), 22.1 frames per take on average; the offline path uses every frame.
- **Not the app UI.** The harness loads `/mediapipe/holistic/holistic.js` from the running app (same options as `lib/holistic.ts`: model complexity 0, smoothing on, CPU inference) and applies the same y rescaling as `toFrame`, but it does not run the app's own React code, getUserMedia, or the WebSocket. Classification used the backend code in process, not the socket. Frames were stored as JPEG quality 95.
- 100 videos give wide intervals (95 percent Wilson interval about plus or minus 9 points). Only classes with a video in `zips_keep` can be drawn. One sample per class, so the numbers are not the full test accuracy (0.913 on 816 samples).
- Detection was not the problem: the body pose was found in 100 percent of frames in every source, hands in about 87 percent.

## Results (n = 100)

Accuracy = answered correctly (above the 0.7 threshold). Wrong accepted = answered above the threshold with the wrong sign. Unrecognized = best guess below the threshold. Top-1 is the best guess ignoring the threshold.

| Source | Accuracy (95% interval) | Wrong accepted | Unrecognized | Top-1 | Accuracy among answered |
|---|---|---|---|---|---|
| offline | 0.82 (0.73 to 0.88) | 0.03 | 0.15 | 0.92 | 0.96 |
| py16x9 | 0.81 (0.72 to 0.87) | 0.03 | 0.16 | 0.90 | 0.96 |
| **br16x9** | **0.78** (0.69 to 0.85) | **0.02** | **0.20** | 0.87 | 0.98 |
| py4x3 | 0.70 (0.60 to 0.78) | 0.05 | 0.25 | 0.81 | 0.93 |
| **br4x3** | **0.65** (0.55 to 0.74) | **0.07** | **0.28** | 0.78 | 0.90 |
| py4x3_raw (no y rescale) | 0.08 | 0.29 | 0.63 | 0.12 | 0.22 |
| br4x3_raw (no y rescale) | 0.07 | 0.29 | 0.64 | 0.10 | 0.19 |

Paired comparison on the same videos (both correct, only the first, only the second; exact sign test):

| Pair | Both | Only first | Only second | p |
|---|---|---|---|---|
| offline vs br16x9 | 76 | 6 | 2 | 0.29 |
| offline vs br4x3 | 60 | 22 | 5 | 0.002 |
| py16x9 vs br16x9 (same frames) | 75 | 6 | 3 | 0.51 |
| py4x3 vs br4x3 (same frames) | 62 | 8 | 3 | 0.23 |

Diagnostics, Python only, same sampled frames:

| Input | Accuracy | Wrong accepted | Unrecognized |
|---|---|---|---|
| 16:9 resized to 640x360 (small picture, no rescale needed) | 0.80 | 0.04 | 0.16 |
| 16:9 centre cropped to 4:3, 640x480, y rescaled (webcam-like fill) | 0.76 | 0.04 | 0.20 |

Per-video rows (label, top guess, confidence, accepted) are in `browser_path_rows.json`. The scripts are in `tools/browser_path/` (see the header of each file; they need the backend venv and `playwright-core`, and write their frames next to themselves, which is git-ignored).

## Reading

1. **Native 16:9 is fine.** The browser path is 4 points below offline (0.78 against 0.82), 6 videos lost and 2 gained, not distinguishable from noise at n = 100. Wrong accepted is as low as offline.
2. **The browser MediaPipe build costs little.** On identical frames it is 3 to 5 points below Python MediaPipe, again not significant. Resolution is not the cause of the 4:3 loss: a 640x360 16:9 picture gives 0.80.
3. **4:3 letterboxed is clearly worse than offline**: 0.65 against 0.82, 22 videos lost and 5 gained (p = 0.002), wrong accepted 7 percent against 3 percent, 28 percent unrecognized. Python MediaPipe on the same 4:3 frames is at 0.70, so most of the loss is in the input, not in the browser.
4. **The y rescale that is now in the app matters a great deal.** Without it 4:3 input gives 0.07 with 29 percent confident wrong answers. With it the same landmarks give 0.65. This also explains the three wrong results of the earlier fake camera test (the earlier test was run before the rescale).
5. **A webcam-like fill is better than a letterbox**: a centre crop to 4:3 with the rescale gives 0.76, 6 points below 16:9, so real webcam behaviour sits between the letterboxed 4:3 and native 16:9 numbers. Real webcam, lighting and signers are still unmeasured (the guided recordings will measure that).

## Proposed fix (not done, no retraining yet)

The remaining loss is a train and input mismatch, so the model, not the pipeline, should be made robust to it:

- **Augmentation during training** on the normalized landmarks: random y scale in 0.75 to 1.35 (covers 4:3, 16:9, 3:2 and a slightly wrong rescale), random uniform scale (the shoulder width normalization removes most of it, so a small jitter of the shoulder estimate), small landmark noise, and random dropping of a hand for a few frames (the browser finds hands in about 87 percent of frames). The pilot found augmentation within noise on INCLUDE alone; this benchmark is the better test of whether it helps, evaluated on the browser frames of the validation videos, not on the test videos.
- **Train on webcam conditions**: the guided sessions record real browser landmarks; including the training signers' takes (S01 to S03) is the direct fix for domain shift.
- **Capture guidance**: ask the user to fill the frame with head, shoulders and both hands (the centre crop result), and show the existing framing hint when the signer is small in the picture.
- **Do not lower the 0.7 threshold or loosen UNRECOGNIZED** to hide the 4:3 loss; the wrong-accepted rate is already higher there.

Before any retraining, re-run this benchmark on validation videos to pick the augmentation ranges, and keep the test videos for one final run.

## Validation run: how much mismatch the model tolerates (to choose augmentation ranges)

Same method on 100 validation videos (one per class, seed 0, split "val" of the authors' predefined split, signer independence not verified; these are not test videos). Nothing was retrained. Accuracy is answered correctly at threshold 0.7; the second number is wrong accepted. The perturbations are applied to the browser landmarks that the app sends (16:9 frames unless stated), so the first row of each sweep is the baseline.

| Source | Accuracy | Wrong accepted |
|---|---|---|
| offline (stored features) | 0.77 | 0.04 |
| browser 16:9 | 0.75 | 0.01 |
| browser 4:3 letterboxed, y rescaled | 0.58 | 0.04 |
| browser 4:3 without the rescale | 0.03 | 0.33 |

The test videos gave the same picture (0.82, 0.78, 0.65, 0.07), so the ordering is not an accident of one sample.

Sensitivity to the y scale (factor applied on top of the correct rescale; 1.0 is exact):

| Factor | 0.6 | 0.75 | 0.9 | 1.0 | 1.1 | 1.25 | 1.33 | 1.5 | 1.75 |
|---|---|---|---|---|---|---|---|---|---|
| Accuracy on 16:9 | 0.01 | 0.05 | 0.43 | 0.75 | 0.65 | 0.26 | 0.14 | 0.05 | 0.01 |
| Accuracy on 4:3 | 0.02 | 0.03 | 0.35 | 0.58 | 0.54 | 0.22 | 0.12 | 0.02 | 0.01 |

The model is very sensitive to the vertical scale: a 10 percent error costs 10 to 30 points and 25 percent leaves 0.2 to 0.3 with 36 to 47 percent wrong accepted. A factor of 0.75 on 16:9 is exactly what an unrescaled 4:3 camera produces, which is why that case failed so badly. This is also why the model cannot be trusted with any camera whose aspect is not reported correctly.

Other perturbations on 16:9 landmarks: Gaussian noise on x and y (in image fractions) 0.002 gives 0.74, 0.005 gives 0.72, 0.01 gives 0.70, 0.02 gives 0.44. Hands removed independently in a random share of frames: 10 percent gives 0.77, 20 percent 0.69, 40 percent 0.55, 60 percent 0.30 (the browser finds a hand in about 87 percent of frames already).

### Proposed augmentation ranges (for the later training run, not applied)

- **Vertical scale**: uniform in 0.85 to 1.20 on the landmark y before normalization, applied to most training samples. This is deliberately narrower than the 0.75 to 1.35 first guessed: the model has no tolerance beyond 20 percent and wider ranges would mostly teach it to ignore a cue that is real (body proportions). The purpose is a safety margin of about 10 percent around the exact rescale (field of view, a camera that reports 16:10, small errors), not coverage of an unrescaled 4:3 camera, which the app now corrects.
- **Landmark noise**: Gaussian, sigma drawn up to 0.01 of the image size (accuracy loss at 0.01 is about 5 points, 0.02 is too much).
- **Hand dropout**: per frame and hand with probability up to 0.2.
- Keep the 0.7 threshold; evaluate each augmentation setting by validation macro F1 and by this benchmark on the browser landmarks of the validation videos, then run the test videos once.

### What augmentation will probably not fix

On exact rescaling the 4:3 letterboxed input is still 17 points below 16:9 on validation (0.58 against 0.75), and a y scale error cannot explain it. The likely cause is MediaPipe itself on a small, letterboxed picture (the Python run on the same frames shows most of the same loss), so the more reliable fixes are capture guidance (fill the frame) and training on real webcam takes. Treat augmentation as a margin, not as the cure.

Files: `tools/browser_path/sweep.py` (run in a copy of the folder whose `samples.json` is `samples_val.json`, produced by `select_samples.py` with the split set to `val`) and `docs/evaluation/browser_path_validation_sweep.json`.
