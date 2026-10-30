# Project completion audit (Phase 14, 2026-10-29)

Auditor stance: evidence only. An item is **Verified** only if a command, test, or observation in this audit demonstrated it.
Documentation and UI appearance alone never count.

## Classification

| Level | Reached? | Why |
|---|---|---|
| **Software foundation** (startup, API integration, validation, configuration, software tests) | **Yes** | Section 2: full test script passes, both servers start, API and UI integrate, containers build and run |
| **Functional prototype** (a documented limited vocabulary with real translation behaviour **and** verified sign animations; recognition only with a real trained model) | **No** | 0 verified sign clips; no trained model; vocabulary is an unvalidated placeholder |
| **Research-ready system** (authorized data, reproducible training, held-out evaluation, genuine metrics, verified animations, documented limitations) | **No** | No dataset, no model, no metrics, no reviewed animations. Tooling and documentation exist, evidence does not |

## 1. Completion matrix

| # | Area | Status | Evidence |
|---|---|---|---|
| 1 | Frontend startup and production build | **Verified** | `scripts\test.ps1`: `build=0` (Next 16.4.3, static `/`); `scripts\dev.ps1` started the dev server, `GET /` 200; browser rendered the page |
| 2 | Backend startup and health endpoint | **Verified** | `dev.ps1` started uvicorn; `GET /api/health` returned `{"status":"ok",...}`; startup log line reports model state; container health check |
| 3 | Webcam capture and permission handling | **Partially verified** | Browser: Start camera showed the permission-denied message (`useLandmarkCapture.ts`, `camera.test.ts`). **No real camera was ever used**: capture, overlay and frame rate are unobserved |
| 4 | MediaPipe landmark extraction | **Partially verified** | Browser: all MediaPipe files load (200) and the status turns "Landmark extraction ready" under React 19. Python MediaPipe ran on a blank frame. **No landmarks from a real person were observed** |
| 5 | Dataset availability and authorization | **Blocked** | INCLUDE is open on Zenodo (CC BY 4.0 in the record metadata) but a derived record claims CC BY-NC-SA 4.0, no signer metadata, 56.75 GB. Nothing downloaded; awaiting your decision (`DATASET_GUIDE.md`) |
| 6 | Model training and checkpoint availability | **Blocked** | `backend/models/` contains only `.gitkeep`. Pipeline works on synthetic data (`test_training_pipeline.py`, `test_phase11_tools.py`) |
| 7 | Genuine ISL recognition inference | **Blocked** | Live `POST /api/signs/translate` returned 503 "No trained recognition model"; `model/status` = `not_trained`. Inference code path tested only with synthetic models |
| 8 | Recognition-to-gloss mapping | **Partially verified** | `translation/labels.py`, `services/recognition_service.py`; `test_integration.py` (synthetic classes through real normalization). No real labels exist |
| 9 | Gloss-to-English translation | **Partially verified** | `test_translation.py`, round-trip test; **placeholder 13-gloss vocabulary, token-by-token**, no signer validation |
| 10 | English-to-gloss translation | **Partially verified** | Live: "Hello, what is your name?" gives `HELLO YOU NAME WHAT`, coverage 1.0; tests. Placeholder vocabulary; ordering rule is an unvalidated assumption |
| 11 | Rigged 3D avatar | **Partially verified** | A procedural 20-bone humanoid renders and moves (browser screenshots, `validateRig` tests). It is not a licensed rigged GLB model and has no face or finger segments (`AVATAR_ASSET_AUDIT.md`) |
| 12 | Verified sign-specific animation clips | **Blocked** | `frontend/public/animations/` is empty; `GET /api/avatar/registry` totals: 0 verified, 0 unreviewed, 13 without any clip. A temporary generic arm-raise clip was used only to test the pipeline, then deleted |
| 13 | Animation playback controls | **Verified (mechanics)** | `playback.test.ts`, `avatar.test.ts` (play, pause, replay, stop, reset, restart, speed, blending, order); browser run with the temporary clip: sequential playback, current-token highlight, Stop. Mechanics only, not sign content |
| 14 | Frontend/backend integration | **Verified** | Browser: status panel and English tab call the API; containerized web UI reached containerized API across origins; CORS tests; `test_integration.py` |
| 15 | Automated and manual tests | **Partially verified** | Automated: 98 pytest + 34 vitest + tsc + ESLint all pass (section 2). Manual testing is limited: no physical camera, no mobile layout check, no keyboard-only pass, no ISL signer review |
| 16 | Security and privacy | **Partially verified** | `npm audit` 0, `pip-audit` none (torch `+cpu` and MediaPipe WASM not covered); no secrets; body cap; no path leak; headers; no frame recording by code search. **No CSP, rate limiting, auth, TLS; no penetration test** (`DEPLOYMENT_READINESS.md`) |
| 17 | Windows setup documentation | **Partially verified** | `setup.ps1` (exit 0), `test.ps1` (exit 0) and `dev.ps1` were executed; each on this already-configured machine, not on a fresh one |
| 18 | Research reproducibility and evidence | **Blocked** | `EXPERIMENT_PLAN.md`, `PROJECT_REPORT.md`, `IEEE_PAPER_CHECKLIST.md`, seeds and `metrics.json` tooling exist; **no experiment results**. IEEE verdict: insufficient evidence |
| 19 | Deployment readiness | **Partially verified** | API and web images built (1.48 GB, 460 MB) and run; `docker compose up` not run; no public deployment (and none performed); reasons it is not public-ready are listed |

## 2. Acceptance tests run (Phase 14)

| Command | Outcome |
|---|---|
| `.\scripts\test.ps1` (backend pytest, `tsc --noEmit`, `eslint .`, `vitest run`, `next build`) | exit 0; `backend pytest=0 tsc=0 lint=0 vitest=0 build=0`; 98 passed (16.9 s); 34 passed in 6 files; build compiled |
| `.\scripts\dev.ps1 -ApiPort 8010 -WebPort 3011` | both windows started; `GET /api/health` 200 and `GET /` 200 within 20 s; CORS header equals the web origin |
| `pip check`; `pip-audit -r requirements.txt`; `npm audit` | clean; no known vulnerabilities; 0 vulnerabilities |
| Live API, no model: `POST /api/signs/translate` | 503 with the "no trained model" message and no predictions |
| Live API: english-to-gloss, avatar plan, registry | `HELLO YOU NAME WHAT` (coverage 1.0); plan `playable: false` ("nothing can be played"); registry 13 no_clip |
| `python -m training.validate_dataset --dir ..\data` | `INVALID: dataset_info.json not found` (no dataset) |
| `python -m training.evaluate ...` with no model | `Error: models\metrics.json not found` |
| Browser on the new stack (Next 16 / React 19 / R3F 9) | status panel live; Start camera shows permission-denied; extractor "ready"; rig self-test moves the avatar; no failed requests |
| Docker: build both images, run API (18000) and web (13000), browser | succeeded; "Backend connected" from the containerized UI |
| Dataset validation, model loading/evaluation on real artifacts | **Not applicable: none exist** |
| Avatar tests on real sign assets | **Not applicable: none exist** |

## 3. Workflows

**ISL to English: BLOCKED (partially implemented).** Webcam, landmarks, trained model, prediction, gloss, English. The
chain's code exists and passes tests with a synthetic model; the live system returns 503 because no real model exists, and
real-camera capture was not observed. No claim of working recognition is made.

**English to ISL: PARTIALLY IMPLEMENTED, NOT FUNCTIONAL AS SIGNING.** English input, gloss from the real API, animation
registry, then avatar. The first two steps work live; the registry reports no clips, so the avatar cannot sign. The only
motion available is a labelled rig self-test that is not a sign.

## 4. Defects found and fixed during Phases 9 to 14

- Phase 7 claim that server error details reached the UI was false for POST requests; fixed (`api.ts`).
- Corrupt checkpoint raised an uncaught pickle/struct error; now a `ModelLoadError`/`error` status.
- `/api/model/status` leaked an absolute local path; fixed.
- Vulnerable dependency stacks upgraded (Next, FastAPI/Starlette, PyTorch, vitest); UI code adapted to React 19 rules.
- Stale results could appear after the camera stopped; results are now tagged by camera run.

## 5. Items in the working tree that this project did not create

Created at 22:38 today by something outside this work (not read, not modified, not part of the project): `.agents/`,
`.cursor/` (includes an MCP config), `.github/copilot-instructions.md`, `.mcp.json`, `.windsurfrules`, `AGENT.md`, `CLAUDE.md`,
`.jetro/` and `.snapshots/`, and empty folders `data/datasets`, `data/lists`, `data/stocks`. Review them before any
commit; MCP configuration files can grant tool access. A leftover root `node_modules/` predates this project.

## 6. Final list

**Verified features:** startup and build of both apps; health, CORS, validation and error handling; status reporting of
missing model/clips; English-to-gloss and gloss-to-English rules (as placeholders); animation plan and registry logic;
avatar rendering and playback mechanics; setup/test/dev scripts on this machine; container builds and runs; dependency
audits clean.

**Unresolved blockers (need you or external resources):** (1) decision on the INCLUDE license conflict and the 56.75 GB
download, or another authorized ISL dataset; (2) ISL signer or linguist for vocabulary, clips and review; (3) a physical webcam
test; (4) a licensed rigged avatar if desired; (5) target venue and template for the paper; (6) CSP, rate limiting and TLS
before any public deployment; (7) review of the unexpected files in section 5.
