# Appendix A: Setup and Run Steps

All commands are Windows PowerShell commands run from the repository root. The code is portable but the provided scripts are Windows only. Node.js 20 or newer, Python 3.11 and Git are needed.

## Setup

```powershell
.\scripts\setup.ps1          # backend\.venv with PyTorch (CPU), MediaPipe, spaCy, FastAPI; npm install in frontend
```

## Files that are not in the repository

The repository does not contain the data, the trained model, the clips or the avatar, on purpose (licence and terms). Without them the application still starts and says what is missing.

Table: Files that are not in the repository and what happens without them. {#tab:missing}
| Missing file | What happens without it | How to get it |
|---|---|---|
| backend/models (isl_model.pt, labels.json, threshold.json) | Sign to English says the model is not trained | train it (docs/MODEL_TRAINING.md) |
| frontend/public/animations/*.json | English to Sign shows no clip for every word | build the clips with the retargeting tool from the INCLUDE features |
| frontend/public/avatar/signer.glb | a built-in procedural figure is used | convert a Mixamo FBX that you download yourself with tools/avatar; confirm the Mixamo terms first |
| frontend/public/mediapipe/holistic | landmark extraction cannot load | npm run setup:mediapipe (copied from node_modules, runs before dev and build) |

## Run

The production build is recommended.

```powershell
.\scripts\serve.ps1          # builds the frontend, starts the API on :8000 and the web app on :3000
```

Open http://localhost:3000. The API needs about 15 seconds to start because it loads spaCy and the model; its interactive documentation is at http://127.0.0.1:8000/docs. To run on other ports (the web build bakes in the API address, so it must be rebuilt):

```powershell
.\scripts\serve.ps1 -ApiPort 8110 -WebPort 3110
```

Running by hand:

```powershell
cd frontend; npm run build; npm start
cd backend; .\.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

For editing the code use `.\scripts\dev.ps1`. A Docker composition exists (run docker compose up with its build option) but was not part of the final verification.

## Using the application

- **Conversation** is the default tab: sign in front of the camera, send the recognized sentence, or type a message for the avatar.
- **Sign to English**: press Start camera and allow the permission, then press Recognize sign after one isolated sign, or switch on Continuous signing and lower the hands between signs. Results below the confidence threshold are shown as unrecognized.
- **English to Sign**: type a sentence, press Translate and then Play.
- **Landmark check**: record 4 seconds, download the video and the landmark file, and compare them offline.
- **Record sign**: single sign or guided session; takes are saved as landmarks only under data/recorded.
- Keyboard shortcuts when not typing: P play or pause, A replay, U undo the last sign, C clear, S send the signed sentence, R recognize or record.

## Tests

```powershell
.\scripts\test.ps1           # pytest, tsc, eslint, vitest and the production build (stop dev servers first)
```

## Training and evaluation

```powershell
cd backend
.\.venv\Scripts\python -m training.compare_models --manifest ..\data\processed\include_v2\manifest.csv --out ..\data\models_v2 `
    --results ..\docs\evaluation\results.md --epochs 60 --patience 10 --max-gap 3 --threads 8
# add --deploy-augment for the deployment augmentation and --checkpoint to write checkpoints (--resume to continue a run)
```

The browser-path benchmark is described in `docs/evaluation/BROWSER_PATH.md` and its scripts are in `tools/browser_path`.

## Deployment

The deployment on Vercel (web) and Hugging Face Spaces (API) is described step by step in `docs/DEPLOYMENT.md`. Nothing has been deployed. Build the Space folder with `.\scripts\make_space.ps1`, test the container locally with Docker, and follow the document for accounts, secrets and environment variables.

## Rebuilding this report

```powershell
python paper\report\make_diagrams.py     # architecture and pipeline diagrams (matplotlib)
python paper\report\make_charts.py       # charts from docs/evaluation and the skeleton figure
python paper\report\build_report.py      # the Word file; Word is used to update the table of contents and to count pages
```

The summary file `docs/evaluation/three_seed_summary.json`, written by `tools/browser_path/three_seed.py`, holds the keys used in the three-seed tables (`model.condition` for the means, `delta.architecture.condition.metric` for the differences) and fills them at each build.
