# Experiment plan

Status: **plan only. No experiment has been run and no result exists.** Every table below is a template to be filled
from files the tooling writes (`backend/models/metrics.json`, `docs/benchmarks/*.json`). Do not enter numbers that
were not produced by those tools.

## 1. Research questions

- RQ1: How accurately can a landmark-based BiGRU recognize isolated ISL signs from an authorized dataset, on signers not
  seen in training?
- RQ2: How much of a target sentence set does the rule-based English-to-gloss baseline cover (supported vs unsupported
  words), and how many of the resulting glosses have a reviewed animation?
- RQ3: What latency does each stage of the pipeline add on commodity hardware?

## 2. Pipeline facts (from the code, verified by tests)

| Item | Value | Source |
|---|---|---|
| Landmarks | MediaPipe Holistic: pose 33, left hand 21, right hand 21; face not used | `backend/app/recognition/landmarks.py` |
| Features per frame | 225 = (33 + 21 + 21) x (x, y, z) | `FEATURE_DIM` |
| Coordinates | MediaPipe normalized image coordinates; z as reported (pose z is relative depth, hand z relative to wrist) | MediaPipe output, passed through |
| Normalization | translate to shoulder midpoint (pose 11, 12), divide by 2D shoulder width | `normalize_frame` |
| Missing hand | zero-filled; presence is reported per frame but not fed to the model | `normalize_frame` |
| Missing pose | frame invalid, excluded from model input; <8 valid frames or <4 frames with hands makes the sequence unusable (422) | `process_sequence` |
| Sequence length | variable input, linearly resampled to `seq_len` (default 32), stored in `labels.json` | `resample_sequence` |
| Client buffer | newest 60 frames; cleared on camera stop and after 15 consecutive frames without pose | `frontend/src/lib/landmarks.ts` |
| Left/right | MediaPipe labels used as-is, no mirroring | open risk; training and inference share this convention only if both use MediaPipe directly |
| Preprocessing identity | Training (`training/video_features.py`) and inference (`process_sequence`) call the same `normalize_frame` and `resample_sequence`; `tests/test_pipeline_audit.py` checks that the model input array is identical for both paths | tests |

Known mismatch risks to check once real data exists: (a) the browser (WASM Holistic, model complexity 0) and Python
Holistic (complexity 0, 0.10.14) may differ slightly in landmark values; (b) a 60-frame (~2 s) live window versus the
variable clip length in the dataset changes the temporal scale after resampling; (c) camera frame rate differs from
dataset frame rate; (d) mirrored webcam preview versus dataset orientation.

## 3. Data

Candidates and caveats are in `DATASET_GUIDE.md`. Required before training: a dataset with recorded license, ISL
labels, and signer identifiers (or a documented author-provided split). Planned split: signer-disjoint train / val / test
(`training/data.py`), seed recorded in `metrics.json`. The test split is used once, after model selection on validation.

## 4. Training protocol

BiGRU (hidden 128, 2 layers, dropout 0.3), Adam lr 1e-3, batch 16, Gaussian noise augmentation 0.01, early stopping on
validation macro-F1 (patience 8), seeds 0 to 4 for variance. Hyperparameter changes are tracked in `metrics.json`.

## 5. Metrics to report (all produced by `training/metrics.py`)

Accuracy; macro precision, recall and F1; per-class P/R/F1/support; confusion matrix; sample, class and signer counts per
split; mean and standard deviation over seeds. Baselines to add if time allows: majority class; nearest-neighbour on
resampled features.

| Split | Samples | Classes | Signers | Accuracy | Macro-P | Macro-R | Macro-F1 |
|---|---|---|---|---|---|---|---|
| Validation | pending | pending | pending | pending | pending | pending | pending |
| Test | pending | pending | pending | pending | pending | pending | pending |

## 6. Translation and animation coverage

Procedure: fix a sentence list (with source and annotator), run `POST /api/translation/english-to-gloss`, record
`coverage` per sentence, the unsupported-phrase rate, and the share of resulting glosses with a clip marked reviewed.
Translation quality needs ISL signer judgement; the rule baseline is not validated and no quality claim is made.

## 7. Latency measurement

Tool: `python -m benchmarks.measure` (see `MODEL_TRAINING.md`). Measured so far (Phase 9, one run, n=100 per item,
hardware in the JSON): preprocessing 60 frames, API round trips, and Python MediaPipe on a blank frame (lower bound).
Not measured: in-browser extraction, model inference (no model), end to end. To report end-to-end latency, run with a
real camera and model, at least 100 recognitions, and give median and p95 with hardware and browser versions.

## 8. Threats to validity

Dataset signer overlap or unknown split independence; small vocabulary; label noise; recording conditions; MediaPipe
failures on fast hand motion; isolated signs only; placeholder gloss vocabulary; no ISL signer review of any output.
