# SignBridge: ISL ⇄ English Translation AI System

SignBridge is an end-to-end bidirectional Indian Sign Language (ISL) and English communication platform.

## Architecture Guidelines
- **Frontend (`frontend/`)**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Three.js / React Three Fiber (`@react-three/fiber`), MediaPipe Holistic runtime.
- **Backend (`backend/`)**: FastAPI, Pydantic v2 schemas, PyTorch landmark classifiers (a 1D CNN is the live model; BiGRU and Transformer were trained for comparison), spaCy rule-based English to ISL gloss, and heuristic gloss to English.
- **3D Avatar**: Bone hierarchy and skeletal animation player in `frontend/src/lib/avatar/`.
- **Dataset & ML**: 75 Holistic landmarks (pose + hands), normalized coordinates.

## Current state (2026-10-31)
- Live Sign to English: `/ws/predict` WebSocket, one isolated sign per request, confidence threshold 0.7, below it the answer is UNRECOGNIZED. Same preprocessing as training (`normalize_frame`, then `prepare_sequence`).
- English to Sign: text to gloss (`backend/nlp`), clips retargeted from INCLUDE samples (`backend/retarget`), Mixamo avatar. 262 glosses have a clip, 51 do not (`docs/MISSING_SIGNS.md`).
- Tabs: Conversation (chat for both directions, the default), Sign to English (isolated and continuous signing, sign segmentation in `backend/app/recognition/segmenter.py`), English to Sign, Record sign (own takes, landmarks only), Landmark check (browser vs Python MediaPipe on the same video).
- Run: `.\scripts\serve.ps1` (production build, recommended). Check: `.\scripts\test.ps1` (pytest, tsc, eslint, vitest, build). Use the dev server only while editing.
- Latest status and every decision: `docs/PROJECT_STATUS.md` (newest first). Model numbers: `docs/evaluation/results.md`.

## Rules for this repository
- Never invent predictions, metrics or clips. No clip is signer reviewed; do not mark any sign verified.
- Label every result "authors' predefined split, signer independence not verified". The test split is evaluated once per model; pilot results are not reportable.
- INCLUDE licence conflict is unresolved (CC BY 4.0 vs CC BY-NC-SA 4.0); we comply with the stricter one: INCLUDE-derived material may only be shared non-commercially under CC BY-NC-SA 4.0 with attribution (`DATA_NOTICE.md`). Keep `data/`, `backend/models/` and `frontend/public/animations/*.json` out of git anyway.
- Never delete, overwrite or reset `data/raw` or `data/processed`. Mixamo terms are unconfirmed; keep `frontend/public/avatar/` out of git.
- In documents, no em dashes and no double hyphens.
