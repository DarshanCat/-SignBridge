<div align="center">
  <img src="assets/hero-animated.svg" alt="SignBridge" width="100%" />
</div>

# SignBridge

SignBridge is an academic prototype that goes both ways between Indian Sign Language (ISL) and English.

- **Sign to English:** the webcam is read in the browser (MediaPipe Holistic landmarks), a trained 1D CNN recognizes one isolated sign at a
  time, and the recognized glosses are turned into an English sentence.
- **English to sign:** a sentence is converted to ISL gloss with spaCy rules and played as retargeted clips on a 3D avatar.

It is not a complete ISL translator. Read [Known limitations](#known-limitations) before relying on any result.

## Contents

[Status](#status) | [Setup and run](#setup-and-run) | [Features](#implemented-features) | [Results](#results) | [Folder structure](#folder-structure) |
[Tests](#tests-and-checks) | [Limitations](#known-limitations) | [Documents](#documents) | [Data and licences](#data-and-licences)

## Status

| Part | State |
|---|---|
| Dataset | INCLUDE processed completely: 4,284 samples, 262 classes (audit PASS, 8 listed videos do not exist in the released archives) |
| Recognition model | 1D CNN, BiGRU and Transformer trained and evaluated; the CNN is used live |
| Live recognition | WebSocket `/ws/predict`, tested with real test features through the socket; not tested with a real webcam |
| Text to gloss | spaCy rule layer, 80+ unit tests, rules not validated by ISL signers |
| Avatar | Mixamo model driven by retargeted clips; 262 signs have an unreviewed clip |
| Sign recorder | Record tab, quality check, promote command; not tested with a real webcam |
| Signer review | none done: no clip is verified |

## Setup and run

Needs Node.js 20 or newer, Python 3.11 and Git. Windows PowerShell commands (the code is portable, the scripts are Windows only).

```powershell
.\scripts\setup.ps1          # backend\.venv with PyTorch (CPU), MediaPipe, spaCy, FastAPI; npm install in frontend
```

### Files that are not in the repository

The repository does not contain the data, the trained model, the clips or the avatar, on purpose (licence and terms, see
[Data and licences](#data-and-licences)). Without them the app still starts and says what is missing.

| Missing file | What happens without it | How to get it |
|---|---|---|
| `backend/models/` (`isl_model.pt`, `labels.json`, `threshold.json`) | Sign to English says "Model not trained" | Train it: `docs/MODEL_TRAINING.md` |
| `frontend/public/animations/*.json` | English to Sign shows "no clip for X" for every word | `python -m retarget.make_vocabulary --all-include --registry config\sign_registry.json ...` (needs the INCLUDE features) |
| `frontend/public/avatar/signer.glb` | A built-in procedural humanoid is used | `tools/avatar/` converts a Mixamo FBX you download yourself; terms of Mixamo are yours to confirm |
| `frontend/public/mediapipe/holistic/` | Landmark extraction cannot load | `npm run setup:mediapipe` (copied from `node_modules`, runs automatically before `dev` and `build`) |

### Run (production build, recommended)

```powershell
.\scripts\serve.ps1          # builds the frontend, starts the API on :8000 and the web app on :3000
```

Open http://localhost:3000. The API needs about 15 seconds to start (it loads spaCy and the model); its docs are at
http://127.0.0.1:8000/docs. Measured on the development machine, the production build loads the page in 0.25 s against 0.9 s in dev mode,
and the dev server needs about 5 s for its first request. Use `.\scripts\dev.ps1` only while changing the code.

By hand: `cd frontend; npm run build; npm start` and `cd backend; .\.venv\Scripts\python -m uvicorn app.main:app --port 8000`.
Docker: `docker compose up --build` (images were built once earlier; compose was not part of the final verification).

### Using it

- **Sign to English tab:** Start camera (allow the browser permission). The overlay shows the body skeleton and both hands; a line under the
  video says whether shoulders and elbows are visible. Press Recognize sign after one isolated sign; accepted signs build the sentence,
  results below the confidence threshold (0.7) are shown as Unrecognized.
- **English to Sign tab:** type a sentence, Translate, then Play, with speed, pause and replay. Words without a clip are listed, not faked.
- **Landmark check tab:** records a 4 second local video together with the browser's landmarks and offers both as downloads;
  `python -m training.compare_landmarks` (from `backend/`) then compares them with Python MediaPipe on the same video. Nothing is uploaded.
- **Record sign tab:** record a sign INCLUDE lacks (3-2-1 countdown, landmarks only). Promote a good take:
  `python -m retarget.promote --clip ..\data\recorded\WATER\<stamp>.clip.json [--replace]`.

## Implemented features

- **Landmarks:** MediaPipe Holistic in the browser (self-hosted WebAssembly, CPU inference), pose 33 and hands 2 x 21 points, 225 values per
  frame, normalized to the shoulders. Face is not used. Video never leaves the browser; only landmarks are sent.
- **Recognition:** three architectures behind one `build_model`; training, evaluation, calibration and pilot tools in `backend/training/`;
  the same preprocessing for training, REST and WebSocket (tested to 1e-6).
- **Live WebSocket:** `/ws/predict` returns sign, gloss, confidence, alternatives, the gloss sequence and an English sentence; below the
  threshold it returns UNRECOGNIZED and leaves the sentence unchanged.
- **Text to gloss:** spaCy rules (time first, subject object verb, negation after the verb, question words last, dropped articles and
  auxiliaries, fingerspelling markers for unknown words) and non-manual marker tags (`docs/NLP.md`). Gloss to English is a heuristic.
- **Avatar:** Mixamo Y Bot driven by retargeted landmark clips, 0.2 s blended transitions, speed, pause, replay, and a rule-based head
  movement for negation, yes/no and WH questions (an approximation, no face animation).
- **Recorder and promotion:** quality check (at least 20 frames, at most 10 percent frames without body, at most 30 percent without any
  hand), clip retarget, `retarget.promote` with `--replace` protection.
- **Data tooling:** streaming INCLUDE download with resume, supplement run with watchdog (`tools/supplement_watchdog.py`), audit
  (`training.audit_include`), label review.
- **Quality and speed:** loading indicators for each stage, cached API lookups, spaCy preloaded, long cache headers for large static files.

## Results

Test split of INCLUDE, **authors' predefined split, signer independence not verified**; 816 test samples, 262 classes; each model evaluated
once on the test split. Settings, per class accuracy, confusion matrices and accuracy versus coverage: `docs/evaluation/results.md`.

| Model | Top-1 | Top-5 | Macro F1 |
|---|---|---|---|
| 1D CNN (live model) | 0.9130 | 0.9902 | 0.9107 |
| BiGRU | 0.7929 | 0.9730 | 0.7869 |
| Transformer | 0.7328 | 0.9596 | 0.7100 |

The live threshold 0.7 was chosen on the validation split (at least 95 percent accuracy on answered samples). On the test split it answers
86.8 percent of the signs with 95.5 percent accuracy and returns Unrecognized for the rest. Model inference takes about 0.4 ms per sign on
the development CPU (median of 200 runs); network and landmark extraction dominate the delay.

Through the live socket, 80 real test samples (rebuilt into landmark frames) gave exactly the offline model's labels and confidences
(80 of 80 identical within 1e-4). The pilot runs that chose the settings (partial data, validation only) are in `docs/evaluation/pilot/`
and are not reportable results.

These numbers describe isolated INCLUDE signs. They are not an estimate of accuracy for a new signer, a webcam, or continuous signing.

## Folder structure

```
backend/
  app/            FastAPI app: api (routes, WebSocket), recognition (features, models, inference), avatar (clips, registry),
                  services, schemas, recording.py (sign recorder)
  nlp/            spaCy text to gloss, gloss to English, gloss dictionary loader
  training/       dataset tools, train, compare_models, calibrate, pilot, audit_include, INCLUDE download and supplement
  retarget/       landmarks to avatar bones, clip builder, make_vocabulary, make_clip, promote
  config/         gloss_dictionary.json, sign_registry.json, translation.json
  models/         trained weights (git-ignored)
  tests/          pytest suite (synthetic data only)
frontend/
  src/app, src/components    Next.js 16 pages and panels (camera, prediction, English to Sign, Record sign)
  src/lib                    landmarks, MediaPipe loader, overlay, prediction socket, recorder, avatar (player, retarget, nmm)
  public/mediapipe, avatar, animations   self-hosted MediaPipe files, signer.glb, clips (the last two are git-ignored)
data/             raw, processed (INCLUDE features v1 and v2), recorded takes (git-ignored)
docs/             project documents, docs/evaluation (audit, results, pilot)
scripts/          setup.ps1, dev.ps1, serve.ps1, test.ps1
tools/            avatar conversion (Blender), supplement watchdog
```

## Tests and checks

```powershell
.\scripts\test.ps1           # backend pytest, tsc, eslint, vitest and the production build (stop dev servers first)
```

Last full run (2026-10-31): backend pytest 277 passed, `tsc` clean, `eslint` clean, vitest 67 passed, `next build` ok. Backend tests use tiny
synthetic models; their scores are not results. See `docs/PROJECT_STATUS.md` for the exact run.

## Known limitations

- **No face features.** Only pose and hands are tracked, and the avatar has no face animation. Non-manual markers are a small rule-based head
  movement, not taken from signer data. Real ISL also uses eyebrows, eyes and mouth.
- **Signer independence is unverified.** INCLUDE publishes no signer IDs, so the predefined split may share signers between train and test.
  Reported accuracy is probably optimistic for new signers.
- **Licence conflict.** INCLUDE is CC BY 4.0 on Zenodo and CC BY-NC-SA 4.0 on a third party page (unresolved). This project follows the
  stricter one: INCLUDE-derived material is non-commercial only, with attribution, under CC BY-NC-SA 4.0 (see [Data and licences](#data-and-licences)).
  Eleven early clips are still in the git history; data, features, models and newer clips are kept out of git.
- **Mixamo terms are unconfirmed.** The avatar model is a Mixamo asset and is not included. Download it yourself and check the terms before sharing it.
- **No clip is signer-reviewed.** All 262 clips are automatic retargets of one training sample each, with approximate bone mapping; some
  will look wrong. Nothing is marked verified, and the registry cannot mark a sign verified without a recorded human review.
- **Missing signs.** 262 of 313 dictionary glosses have a clip; 1 INCLUDE class has no data and 50 grammar words (NOT, WHAT, WHERE, GO, HELP,
  YES, NO, ...) have none; fingerspelling clips do not exist (`docs/MISSING_SIGNS.md`).
- **Isolated signs only.** Continuous signing is not segmented; each Recognize press is one sign, and gloss to English is a heuristic.
- **Browser versus training features.** Training features came from Python MediaPipe on video; the browser uses the WebAssembly build with
  CPU inference. The difference is untested with a real webcam and may lower accuracy.
- **Text to gloss rules are assumptions** (`docs/NLP.md`), not validated by ISL signers.
- **Vocabulary:** 262 INCLUDE classes only, everyday words outside them are unknown.

## Documents

`docs/PROJECT_STATUS.md` (dated log of every step), `docs/MODEL_TRAINING.md`, `docs/NLP.md`, `docs/AVATAR_RETARGET_PLAN.md`,
`docs/API_REFERENCE.md`, `docs/MISSING_SIGNS.md`, `docs/evaluation/` (audit, results, pilot), `docs/LABEL_REVIEW`
(`docs/evaluation/LABEL_REVIEW.md`). Older documents in `docs/` (for example `PROJECT_REPORT.md`, `DEPLOYMENT_READINESS.md`) were written
before the model existed and may be out of date; `PROJECT_STATUS.md` wins where they disagree.

## Data and licences

Full details: **[DATA_NOTICE.md](DATA_NOTICE.md)**.

- **Code:** the MIT licence (`LICENSE`) covers the original code only. It does **not** cover INCLUDE or anything derived from it.
- **INCLUDE-derived material** (the clips in git history, statistics in `docs/evaluation/`, and any features, models or clips you build from the
  data) is treated as **CC BY-NC-SA 4.0: non-commercial only, with attribution, share alike**. The dataset's own licence is unresolved (CC BY 4.0 on
  Zenodo, CC BY-NC-SA 4.0 on a third party page), so the project follows the stricter one. Cite: Sridhar, Ganesan, Kumar and Khapra, INCLUDE,
  ACM Multimedia 2020, DOI 10.1145/3394171.3413528, and Zenodo record 4010759.
- **Mixamo avatar:** not included. Download your own model from Mixamo and convert it with `tools/avatar/`; check Mixamo's terms yourself.
- **Kept out of git on purpose:** `data/`, `backend/models/`, `frontend/public/animations/*.json`, `frontend/public/avatar/`.

Author: Darshan BG ([@DarshanCat](https://github.com/DarshanCat)). Built with MediaPipe, PyTorch, spaCy, FastAPI, Next.js and three.js.
