# SignBridge AI Context

SignBridge is an end-to-end bidirectional Indian Sign Language (ISL) and English communication platform.

## Architecture
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS, React Three Fiber (R3F) for 3D avatar rendering, and MediaPipe Holistic for landmark tracking.
- **Backend**: FastAPI, PyTorch landmark classifiers (a 1D CNN is the live model; BiGRU and Transformer were trained for comparison), spaCy rule-based English to ISL gloss, and heuristic gloss to English.
- **Data & Models**: MediaPipe 75 landmarks (Pose + Left Hand + Right Hand).

## Current state (2026-10-31)
- Live Sign to English: `/ws/predict` WebSocket, one isolated sign per request, confidence threshold 0.7, below it the answer is UNRECOGNIZED. Same preprocessing as training (`normalize_frame`, then `prepare_sequence`).
- English to Sign: text to gloss (`backend/nlp`), clips retargeted from INCLUDE samples (`backend/retarget`), Mixamo avatar. 262 glosses have a clip, 51 do not (`docs/MISSING_SIGNS.md`).
- Extra tabs: Record sign (own takes, landmarks only), Landmark check (browser vs Python MediaPipe on the same video).
- Run: `.\scripts\serve.ps1` (production build, recommended). Check: `.\scripts\test.ps1` (pytest, tsc, eslint, vitest, build). Use the dev server only while editing.
- Latest status and every decision: `docs/PROJECT_STATUS.md` (newest first). Model numbers: `docs/evaluation/results.md`.

## Rules for this repository
- Never invent predictions, metrics or clips. No clip is signer reviewed; do not mark any sign verified.
- Label every result "authors' predefined split, signer independence not verified". The test split is evaluated once per model; pilot results are not reportable.
- INCLUDE licence conflict is unresolved (CC BY 4.0 vs CC BY-NC-SA 4.0): non-commercial academic use with attribution, no redistribution of data, features, derived clips or model weights. Do not commit `data/`, `backend/models/` or `frontend/public/animations/*.json`.
- Never delete, overwrite or reset `data/raw` or `data/processed`. Mixamo terms are unconfirmed; keep `frontend/public/avatar/` out of git.
- In documents, no em dashes and no double hyphens.
