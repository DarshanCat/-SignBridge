# Model training

Status: trained and evaluated on the complete INCLUDE data (v2). Numbers are in `docs/evaluation/results.md`; the label that goes with
every number is "authors' predefined split, signer independence not verified".

## Data

`data/processed/include_v2/manifest.csv`: 4,284 samples, 262 classes, split train 3,121 / val 347 / test 816 exactly as the authors' lists
define it (`docs/evaluation/DATASET_QUALITY_AUDIT.md`, result PASS with one documented exception). The raw data, features and
derived clips are kept out of git and shared only non-commercially under CC BY-NC-SA 4.0 with attribution (see `DATA_NOTICE.md`).

## Features

Per frame 225 values: pose (33), left hand (21), right hand (21) landmarks as x, y, z, origin at the shoulder midpoint, divided by shoulder
width (`app/recognition/landmarks.py`). A missing hand is an all zero block. Frames without a body pose are dropped. Sequences are resampled
linearly to `seq_len` 32 (`app/recognition/preprocess.py`); optional hand gap interpolation (`max_gap`) fills short hand dropouts. Face
landmarks are not used.

## Models (`app/recognition/models.py`)

1D CNN, BiGRU and Transformer encoder, built by `build_model` from the `ModelConfig` stored in `labels.json`, so the same code path loads a
checkpoint for training, evaluation and the API.

## Commands (from `backend/`, PowerShell)

```powershell
# Train all three on the same split and seed, evaluate the test split once per model, write docs/evaluation/results.md
.\.venv\Scripts\python -m training.compare_models --manifest ..\data\processed\include_v2\manifest.csv --out ..\data\models_v2 `
    --results ..\docs\evaluation\results.md --epochs 60 --patience 10 --max-gap 3 --threads 8

# Choose the live confidence threshold on the validation split of the best model (writes threshold.json next to it)
.\.venv\Scripts\python -m training.calibrate --manifest ..\data\processed\include_v2\manifest.csv --model-dir ..\data\models_v2\cnn --precision 0.95

# Rebuild results.md from the saved metrics (no retraining, no new evaluation)
.\.venv\Scripts\python -m training.compare_models --manifest ..\data\processed\include_v2\manifest.csv --out ..\data\models_v2 `
    --results ..\docs\evaluation\results.md --reuse --threshold-file ..\data\models_v2\cnn\threshold.json

# Use the best model in the API: copy isl_model.pt, labels.json, metrics.json and threshold.json into backend\models (git-ignored)
```

A single model: `python -m training.train --manifest <csv> --arch cnn|bigru|transformer`. Pilot runs that must not read the test split:
`python -m training.pilot` (the test files are never opened; see `docs/evaluation/pilot/README.md`).

## Settings used and why

1D CNN, BiGRU and Transformer all with 60 epochs maximum, patience 10, `max_gap` 3, learning rate 0.001, hidden size 128, 2 layers,
dropout 0.3, batch 16, seed 0, no augmentation. They were chosen from the pilot runs on the partial v1 data (validation only): the CNN was
clearly best; gap interpolation and augmentation were within noise of each other (differences of about 4 of 299 validation samples), and
the recurrent and attention models were still improving at 40 epochs, so all three got the same larger budget. Early stopping and model
selection use validation macro-F1 only. The test split is evaluated exactly once per model, inside `train()`; nothing was tuned on it.

## Results in one table (test split, authors' predefined split, signer independence not verified)

| Model | Top-1 | Top-5 | Macro F1 |
|---|---|---|---|
| 1D CNN (best by validation) | 0.9130 | 0.9902 | 0.9107 |
| BiGRU | 0.7929 | 0.9730 | 0.7869 |
| Transformer | 0.7328 | 0.9596 | 0.7100 |

Per class accuracy, the most frequent confusions, accuracy versus coverage and full confusion matrices are in `docs/evaluation/`.

## Reading the numbers carefully

- INCLUDE publishes no signer IDs, so the predefined split may share signers between train and test. The numbers measure recognition of
  isolated signs recorded under INCLUDE conditions; they say nothing about new signers, webcams, lighting or continuous signing.
- MediaPipe in the browser (WebAssembly, CPU inference) differs from the Python MediaPipe used to extract the training features. This
  mismatch is untested with real webcam input and may lower accuracy.
- Validation macro metrics average over 246 classes (16 classes have no validation video in the authors' lists).

## Tests

`backend/tests/test_training_pipeline.py`, `test_slr_pipeline.py` and `test_pilot.py` train tiny models on synthetic arrays in temporary
folders to test the code; those models are not real and their scores must never be cited. `test_live.py` checks that the live
WebSocket path produces the same probabilities as the training preprocessing.
