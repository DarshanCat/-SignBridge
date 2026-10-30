# Architecture

## Components

- `frontend/` Next.js 14 (App Router), React 18, Tailwind 3, React Three Fiber 8 and Drei. Talks to the API at
  `NEXT_PUBLIC_API_URL`. MediaPipe Holistic runs **in the browser** from files copied into `public/mediapipe`, so video
  never leaves the machine; only landmark arrays are sent to the API.
- `backend/app/api` routes only. `schemas/` Pydantic models. `core/` settings (env prefix `SIGNBRIDGE_`).
  `services/` orchestration (recognition, avatar plan). `recognition/` landmark normalization, model, artifacts,
  inference, status. `translation/` vocabulary and rule-based translators. `avatar/` clip format and registry.
- `backend/training/` dataset tools and the training script. Training is separate from the API; the API only loads
  artifacts (`isl_model.pt` + `labels.json`) from `backend/models/`.
- `backend/config/translation.json` the editable placeholder vocabulary and rules.

## Pipelines

```
Sign to English
  webcam -> MediaPipe Holistic (browser) -> LandmarkFrame[] -> POST /api/signs/translate
         -> normalize (225 features/frame) -> resample to 32 -> BiGRU -> softmax
         -> confidence gate -> label -> gloss -> English

English to Sign
  text -> POST /api/translation/english-to-gloss (rules + vocabulary)
       -> POST /api/avatar/plan (gloss -> clip files that exist) -> fetch clips -> SequencePlayer -> 3D avatar
```

Each stage reports what it could not do (no model: 503; unusable landmarks: 422; unsupported words; missing clips)
instead of substituting output.

## Decisions

- Landmarks are extracted client-side (privacy, no video upload). Python MediaPipe is used only for offline dataset
  preprocessing, with the same normalization code, so training and inference features match.
- Python 3.11 backend (MediaPipe and PyTorch wheel support). PyTorch CPU build.
- A procedural avatar replaced the preferred rigged GLB because no verified-license asset was available.
- Status indicators are derived from real checks (`frontend/src/lib/status.ts`), never hard-coded as ready.
