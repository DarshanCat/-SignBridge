# Model training

**Status: pipeline implemented and unit-tested; no real model has been trained and no accuracy figures exist.**
No ISL dataset has been obtained yet (see `DATASET_GUIDE.md`).

## Input features

Per frame, 225 values: pose (33), left hand (21), right hand (21) landmarks as x, y, z, centred on the shoulder
midpoint and divided by shoulder width (`app/recognition/landmarks.py`). Missing hands are zeros. Sequences are
linearly resampled to `seq_len` frames (default 32; `app/recognition/preprocess.py`). Face landmarks are not used.

## Model

`BiGRUClassifier` (`app/recognition/model.py`): bidirectional GRU (default hidden 128, 2 layers, dropout 0.3),
mean-pool over time, linear head. PyTorch 2.5.1 (CPU wheel) on Python 3.11.

## Training data format

A manifest CSV with columns `path,label,signer_id`. Each `path` (relative to the manifest) is a `.npy` file of shape
`(T, 225)` produced by the same normalization used at inference. Labels must be ISL glosses, never ASL labels.

## Running

```powershell
cd backend
pip install -r requirements-ml.txt --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python -m training.train --manifest ..\data\processed\manifest.csv --out models --seed 0
```

Training refuses to run with fewer than 3 signers, because the split is signer-independent (disjoint signers for
train/validation/test, chosen by seed). Early stopping uses validation macro-F1; the best checkpoint is kept.
Outputs in `backend/models/` (git-ignored): `isl_model.pt`, `labels.json` (class map, feature dim, seq_len and
architecture, needed to load the weights), and `metrics.json` (accuracy, macro-F1, per-class precision/recall/F1,
confusion matrix, signer lists, hyperparameters, environment) for validation and test.

## Tests

`backend/tests/test_training_pipeline.py` trains on synthetic arrays in temporary directories to test the code. Those
models are not real, are never saved to `backend/models`, and their scores must never be cited.

## Not yet done

Real data, hyperparameter search, augmentation beyond Gaussian noise, latency measurements, any reported results.

## Real-time infrastructure and consistency (Phase 9)

- **Window and sequence length:** the browser keeps the newest 60 frames; the backend drops invalid frames and resamples
  to `seq_len` (default 32). The buffer is cleared when the camera stops and after 15 consecutive frames without a body
  pose. Only one server request can be in flight, and responses that arrive after the camera stopped are discarded.
- **Startup:** the API loads the model during startup (`lifespan` in `app/main.py`) and logs its state; the loaded
  recognizer is cached and reloaded only if `isl_model.pt` changes on disk. With no model the API starts and reports
  `not_trained`.
- **Guards:** `load_artifacts` rejects a checkpoint whose `feature_dim` differs from the pipeline's 225, or an invalid
  `seq_len`/class list; wrong-dimension input to the recognizer is a 422, not a 500.
- **Consistency:** training and inference share `normalize_frame` and `resample_sequence`; `tests/test_pipeline_audit.py`
  asserts the model input is identical on both paths and that the API prediction equals the direct recognizer output.
  Remaining differences (browser vs Python MediaPipe, live window vs clip length) are listed in `EXPERIMENT_PLAN.md`.
- **Latency tool:** `cd backend; .\.venv\Scripts\python -m benchmarks.measure --api http://localhost:8010 --out ..\docs\benchmarks\latest.json`
  (start the backend first). Model inference is measured only if a real model exists.

## Phase 11 tooling

All commands run from `backend/` with the venv's Python. Everything below is tested on synthetic data only.

```powershell
# 1. index videos from a folder tree (label = parent folder; optional signer regex, split file, duplicate hashing)
.\.venv\Scripts\python -m training.make_manifest --root ..\data\raw\<ds> --out ..\data\raw\<ds>\index.csv --hash-duplicates
# 2. extract landmarks (writes manifest.csv and exclusions.csv; failures are listed, never dropped silently)
.\.venv\Scripts\python -m training.preprocess_videos --index ..\data\raw\<ds>\index.csv --out ..\data\processed\<ds>
# 3. validate and write a data-quality report (class/signer counts, lengths, duplicates)
.\.venv\Scripts\python -m training.validate_dataset --dir ..\data\processed\<ds> --report ..\docs\evaluation\<ds>_quality.json
# 4. train (refuses if validation fails; add --class-weights for imbalance)
.\.venv\Scripts\python -m training.train --manifest ..\data\processed\<ds>\manifest.csv --out models --seed 0
# 5. evaluate on the held-out test split (same split as training) and time single-sequence inference
.\.venv\Scripts\python -m training.evaluate --manifest ..\data\processed\<ds>\manifest.csv --model-dir models --out ..\docs\evaluation\<ds>_test.json
```

Splits: if every manifest row has a `split` (train/val/test) it is used as given and reported as `predefined`
(signer independence not verified); otherwise a seeded signer-disjoint split is made (needs at least 3 signers). A
`split` column filled for only some rows is an error. `metrics.json` records the split method, seed, signer lists,
hyperparameters and class-weight choice. The test split is used only for the final numbers; early stopping uses validation.
Metrics: accuracy, macro precision/recall/F1 (over classes with test support), per-class results, confusion matrix.

Production inference never imports `training/`; the API loads `isl_model.pt` and `labels.json` only.

## INCLUDE run (in progress, 2026-10-29)

Order of operations once `data/processed/include/manifest.csv` exists (from `backend\`):

```powershell
.\.venv\Scripts\python -m training.verify_include_split --raw ..\dataaw\include --out ..\data\processed\include --report ..\docs\evaluation\include_split_check.json
.\.venv\Scripts\python -m training.validate_dataset --dir ..\data\processed\include --report ..\docs\evaluation\include_quality.json
.\.venv\Scripts\python -m training.train --manifest ..\data\processed\include\manifest.csv --out models --seed 0 --class-weights
.\.venv\Scripts\python -m training.evaluate --manifest ..\data\processed\include\manifest.csv --model-dir models --out ..\docs\evaluation\include_test.json
```

`--class-weights` is a boolean flag (`store_true`), confirmed in `training/train.py`. Training uses the manifest's predefined split
(`split_method: predefined`); the test split is untouched until `evaluate`, which recomputes the same split and reports
accuracy, macro-F1, per-class metrics and the confusion matrix. **No results exist yet.** Limitations to quote with any result: the
split is the authors' (signer independence unverified, no signer IDs), landmarks were extracted with Python MediaPipe at
frame stride 2, and use is limited to non-commercial academic research until the license conflict is settled.
