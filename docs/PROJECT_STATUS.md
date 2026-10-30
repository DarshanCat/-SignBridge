# Project status

## Licence decision, run progress, recorder and Module A UI (2026-10-30 22:00)

Licence decision (from the project owner): training on INCLUDE is allowed for non-commercial academic use with attribution to the INCLUDE authors (Sridhar, Ganesan, Kumar, Khapra, ACM Multimedia 2020). The conflict stays documented: Zenodo lists CC BY 4.0, a third party page lists CC BY NC SA 4.0. Until it is resolved there is no redistribution of the data, the extracted features or any clip derived from them, and no commercial use. This is not a blocker for Phase 3 (training).

Supplement run progress: 6 of 28 affected zips are complete. Counted only from the completion records (`data/processed/include_v2/_parts_supplement/<zip>.csv`) whose names match the 28 affected zips (derived with `affected_zips` from the first run logs) and whose write time is after the run start (PID 31976, started 20:02:48): Animals_1of2, Animals_2of2, Clothes_1of2, Clothes_2of2, Colours_1of2, Colours_2of2. In progress: the Days_and_Time zips. The older `_parts` folder was not counted. PID 31976 and PID 30504 were not touched.

Sign recorder: new "Record sign" tab (webcam, landmark overlay, gloss name, 3-2-1 countdown, 2 to 5 s take). Only landmarks are sent (`POST /api/record/sign`), normalised to the same 225 features per frame as INCLUDE, and stored under `data/recorded/<GLOSS>/` (`<stamp>.npy`, `.json` metadata with `contains_video: false`, `.clip.json`); `data/recorded/` is git-ignored. Quality check (`backend/app/recording.py`): rejected and not stored if fewer than 20 frames, the measured frame rate is outside 5 to 60 fps, the body is missing in more than 10 percent of frames, or no hand is detected in more than 30 percent of frames; the UI lists the reasons. An accepted take is retargeted with the measured fps into a clip with `review_status: not_signer_reviewed` and `source.origin: self-recorded`, previewed on the avatar. It is not added to `frontend/public/animations` or the sign registry automatically; that is a manual step after review.

Module A UI without a model: the Sign to English tab now has a live prediction panel with the landmark buffer (frames out of 60) and the state of the `/ws/predict` WebSocket stub. With no model it shows "Model not trained" and never a sign, gloss or confidence. The client sends no frames yet because the stub does not read them.

Checks run: `tsc` clean, `eslint` clean, `vitest` 57 passed (new: recorder helpers, prediction channel), `next build` ok, backend `pytest` 247 passed (7 new for the recorder). Browser smoke test: the Record sign tab and the live prediction panel render; the `/ws/predict` stub returned `model_not_trained`. The webcam flow itself (camera, countdown, a real take) was NOT exercised in a browser here, only by unit and API tests with synthetic landmarks. Dev servers stopped.

## Starter vocabulary, text to sign, head markers (2026-10-30 21:40)

Retention check: Colours_1of2 was missed by the first keeper (it polled every 4 s while a zip is processed in about 3 s); a second keeper now hard links the `.part` files, and the two lost zips (Animals_1of2, Colours_1of2) are to be re-fetched only after the supplement run (PID 31976, untouched) ends.

Starter vocabulary: of HELLO, THANK-YOU, HOSPITAL, WHERE, MARKET, GO, YESTERDAY, I, YOU, HELP, the INCLUDE classes that exist are HELLO, THANK-YOU, HOSPITAL, MARKET, YESTERDAY, I, YOU. WHERE, GO and HELP are not INCLUDE classes and were replaced by DOCTOR, BANK and TOMORROW. Each clip is a retarget of the training sample with the fewest no-hand frames (`python -m retarget.make_vocabulary`), stored in `frontend/public/animations/` with `index.json` (gloss to clip). The sample used is recorded in each clip under `source.source_sample`. All are `not_signer_reviewed`; none is a verified sign. WHERE has no clip, so "Where is the hospital?" shows "no clip for WHERE".

Text to sign: the panel calls `POST /api/nlp/text-to-gloss`, shows the gloss, the non-manual tags and a clear "no clip for X" per gloss, and plays the clips in order with 0.2 s blended transitions, speed 0.5x/1x/1.5x, pause, replay and restart. Fingerspelling is used only if every letter has an `FS-<letter>` clip; none exist, so such words show "no clip". No clip is faked.

Head markers: rule-based approximation on the head bone only (negation: shake about 0.22 rad at 2.5 Hz; yes/no question: 0.12 rad forward tilt; WH question: 0.12 rad sideways tilt; 0.3 s ease in and out). Amplitudes are my assumptions, not signer validated; no face is animated. See `docs/NLP.md`.

Checks run: `tsc` clean, `eslint` clean, `vitest` 49 passed (new tests for markers and token availability), `next build` ok, backend `pytest` 240 passed. Visual check in the browser: "Where is the hospital?" played HOSPITAL and listed WHERE as no clip; "I do not like the hospital" played I then HOSPITAL and listed LIKE and NOT as no clip. The head movement amplitude was not judged by eye (small); it is covered by unit tests only. Dev servers stopped.

## Mixamo avatar integrated (2026-10-30 21:00)

Blender 5.2.3 LTS installed with winget (`C:\Program Files\Blender Foundation\Blender 5.2lender.exe`). Your `T-Pose.fbx` was copied to `tools/avatar/source/` (original untouched) and converted
by `tools/avatar/convert_fbx.py` to `frontend/public/avatar/signer.glb` (1.79 MB). Parsed with `tools/avatar/verify_glb.py`: 65 joints, wrist and Thumb, Index, Middle, Ring, Pinky joints 1 to 3 (plus a tip bone)
on both hands, no animations. `SOURCE.md` written (terms: to be confirmed by you before any public release). `frontend/public/avatar/`, `tools/avatar/source/` are in `.gitignore`; the avatar folder is also in `.dockerignore`.

Built: `lib/avatar/mixamo.ts` (bone map, arms-down rest derived from the skeleton, pose application), `components/avatar/GlbHumanoid.tsx` (loads the GLB, falls back to the procedural humanoid), clip JSON
field `review_status: not_signer_reviewed` (backend schema, retarget builder, TypeScript type) and the UI text "clip not signer-reviewed" while playing. Results run: frontend `tsc` clean, ESLint clean,
`vitest` 40 passed (6 new, parsing the real GLB), `next build` ok; backend `pytest` 237 passed. Visual check: retargeted INCLUDE Hello sample on the Mixamo avatar raised the right hand to head height;
temporary clip removed (`frontend/public/animations` empty), dev servers stopped. Not done: the 10 sign starter vocabulary, face and head tilt, any signer review. The convert step used the default exporter settings and the
armature keeps its 0.01 scale and 90 degree rotation node.


## Avatar route chosen: Mixamo rig with INCLUDE landmark retargeting (2026-10-30 20:35)

Decision recorded. Plan, your download steps and limits: `docs/AVATAR_RETARGET_PLAN.md`. I cannot log in to Mixamo or create accounts, so
the rig must be downloaded by you (FBX, convert to GLB, place at `frontend/public/avatar/signer.glb`, add a SOURCE note with the terms you relied on).

Built without the asset: `backend/retarget/` (landmarks to bone rotations, clip builder, command line tool). 16 tests pass (forward kinematics, mirror
symmetry, rest start and end, hand dropout, duration limit); full backend suite run after adding them: 237 passed.
Visual check: the first INCLUDE Hello training sample retargeted and played on the procedural avatar raised the right forearm and hand to head height over
2.9 s. This verifies the geometry, not the sign. The temporary clip was removed; the animations folder is empty again. The dev servers started for the check were stopped.

Run status, corrected at 20:33: my earlier suspicion that the supplement run had stalled was WRONG. Windows file listings (PowerShell) showed the
files being downloaded at 0 MB because their size is not refreshed while they are open; reading them directly showed Clothes_1of2 at about 925 MB and Clothes_2of2
at about 706 MB, so the run was downloading normally. Starvation by my extra download was never shown. At your request I stopped my Animals_1of2 re-download
anyway (partial file of about 750 MB left in `zips_keep` as Animals_1of2.zip.dl; the server cannot resume, so it must be fetched again from the start later).
Supplement run alive (PID 31976), 2 of 28 zips processed so far; keeper (PID 3408) alive; Animals_2of2 is kept in `zips_keep`, Animals_1of2 is not.


## Parallel work while the supplement run continues (2026-10-30 20:25)

Supplement run (PID 31976, not touched): 2 of 28 zips done (Animals 1 and 2: 10 and 6 videos recovered, 0 unmatched, 0 filename fallbacks so far).
Downloads are the slow part; each zip needs only a few videos processed. No model has been trained. `data/raw` and `data/processed` were not modified
(the first manifest was read once, read only, for the smoke run).

Zip retention: the supplement process deletes each zip after processing (its loop was loaded before your request). I could not change it
without touching the process, so I added a hard link keeper (`zips_keep/keep_zips.ps1`, PID 3408) that links each finished zip into `zips_keep/`.
Hard links cost no extra space. **One zip was lost before the keeper worked: Animals_1of2 was processed and deleted.** It is being fetched again
into `zips_keep` (about 1.8 GB). The first keeper launch failed on a path quoting error that I only found later. Please do not delete `zips_keep`.

Phase 3 code (no training): normalization with optional hand gap interpolation, landmark augmentation, manifest loader, 1D CNN, BiGRU and
Transformer, training, evaluation and comparison scripts, metrics (top-1, top-5, macro F1, confusion matrix, per class accuracy, accuracy versus
coverage) and an UNRECOGNIZED output. 23 new tests on synthetic tensors. A one epoch smoke run on a tiny slice of the first manifest ran all three
models end to end; its checkpoints were deleted and its numbers are not reported. See `docs/MODEL_TRAINING.md`.

Phase 4: spaCy rule based English to gloss and gloss to English with fingerspelling fallback and non manual markers; dictionary of 263 INCLUDE signs plus 50
unvalidated grammar placeholders; gloss forms YOU-PLURAL, RACE-ETHNICITY and SECOND-NUMBER. 80 tests (36 English to gloss pairs, 20 gloss to English
pairs, 8 round trips). Both required examples pass. See `docs/NLP.md`. Rules are assumed and unvalidated by ISL signers.

Phase 5 skeleton: `POST /api/nlp/text-to-gloss`, `POST /api/nlp/gloss-to-text`, and `WS /ws/predict` as a stub that returns a clear model_not_trained error and
closes. Config through the environment with `.env.example` (new: spaCy model name, gloss dictionary path). 9 new API tests.

Test results actually run: backend `pytest` 221 passed (full suite, 2026-10-30). Frontend was not changed and not re run. The Dockerfile was updated to include
`nlp` and the spaCy requirements but the image was not rebuilt, so that change is unverified.

Avatar check (nothing built): the project has no rigged avatar asset. No glb, gltf, fbx, vrm, blend, bvh or obj files exist. `frontend/public/animations/` is empty.
What exists is the procedural 20 bone humanoid in `frontend/src/lib/avatar/rig.ts` (boxes, spheres and capsules, one joint per finger, no face), the clip format
and validator, the player and the sign registry (13 placeholder entries, all `no_clip`). Gate 3 options are in the final report of this step.


## Gate 1 interim, decisions and split fix in progress (2026-10-30 20:10, label merge approved 20:08)

Supplement run (PID 31976, `data/raw/include/supplement.log`) is alive: 0 of 28 zips finished, downloads in progress (about 2 hours
expected). It reads the old outputs and writes only to `data/processed/include_v2`. The audit result for the fixed set is therefore
**not available yet**; Phase 3 has not started and no model is trained.

Code changes since: `include_supplement.py` (extension insensitive match, filename fallback, v2 manifest, label policy flag,
manifest only mode), `include_stream.label_of` fixed so nested folders do not become labels, `audit_include.py` extended for v2 (stem
matching, multiple part folders, full lists of videos still missing, every filename_fallback row, classes with no sample in a split).
Unit tests for these pass (11 in the three new test files).

Label review (details and counts in `docs/evaluation/LABEL_REVIEW.md`, awaiting your approval, nothing applied): the four "Extra"
labels were my bug, not classes; they are 27 videos in nested folders under 16 parent classes and are proposed to be merged into
their parents with the authors' split kept; three bracketed labels (you (plural) 21 videos, Race (ethnicity) 14, Second (Number) 8)
are genuine classes that stay separate. **You approved the merge**: the v2 manifest builder now merges the nested Extra videos into their parent classes by default (authors' split kept per video, nothing dropped); gloss strings YOU-PLURAL, RACE-ETHNICITY and SECOND-NUMBER are applied in Phase 3 label to gloss conversion.

Decisions recorded from you (2026-10-30):
1. Frontend: keep the existing Next.js 16 app. Add React Three Fiber, Drei and Tailwind inside it. No migration to Vite.
2. Face landmarks: features stay at 225 per frame (pose and both hands). No re-extraction. Module A trains on pose and hands; the
   missing non manual markers (facial expression for negation and questions) are a documented known limitation. Face expressions
   remain in scope for the avatar only.
3. The 1D CNN baseline, spaCy gloss rules and WebSocket streaming stay in the plan for Phases 3 to 5.
4. The authors' split stays as is; the test split will not be re split.

Still true: licence conflict unresolved (Zenodo record says CC BY 4.0, a third party page says CC BY NC SA 4.0), signer independence
unverified.

## Synopsis and Phase 1 and 2 (2026-10-30)

Read `SignBridge_Synopsis.docx`. Notes against the current build: the synopsis plans face landmarks (not extracted yet),
a 1D CNN, BiGRU and Transformer comparison, spaCy gloss rules, WebSocket streaming, Mixamo or Blender avatar clips, and signer
independent evaluation (INCLUDE has no signer IDs). It names Flask or FastAPI plus HTML or JavaScript; the frontend is Next.js
16, not Vite, which will need your decision at the frontend phase.

Phase 1 is complete: the resumed run finished, all 44 zips have completion records, and `manifest.csv` exists with 3,679 samples
(0 failures, 0 exclusions). Phase 2 audit result: **FAIL**. Integrity passes (no unreadable, malformed, non finite or duplicate
arrays), but 613 of the 4,292 authors' listed videos are missing (train 456, val 49, test 108): the lists say `.MOV` while many
zips store `.MP4`, so 605 videos were skipped as not in the lists (all 54 logged examples confirmed); 8 more are unexplained.
Fixing it needs re-downloading 28 zips (about 36 GB). See `docs/evaluation/DATASET_QUALITY_AUDIT.md`, `dataset_quality.json`,
`class_distribution.csv` and `split_integrity.json`. Licence conflict unresolved (Zenodo record says CC BY 4.0, a third party page
says CC BY NC SA 4.0); signer independence unverified. No model has been trained. Waiting at GATE 1.


## Dataset quality audit: NOT STARTED, processing incomplete (2026-10-30 19:50)

Verified: the resumed run (PID 29280) is alive and processing; **38 of 44 zips are processed** (38 part records, 3,283 feature
files; Places 1 to 4 finished at 103, 106, 104 and 86 usable videos, none unmatched or failed). Pronouns_1of2 is in progress;
**6 zips remain**: Pronouns_1of2, Pronouns_2of2, Seasons_1of1, Society_1of3, Society_2of3, Society_3of3 (all downloaded and
intact). The final `manifest.csv` does not exist yet (it is written only when all 44 are done; the earlier one-zip trial manifest
is kept as `manifest.trial_1zip_STALE.csv` and must not be used). The audit (integrity, split integrity against the authors' lists of
3,127 / 348 / 817, statistics, `docs/evaluation/*` deliverables) was **not run**, as required when processing is incomplete.
Licensing remains unresolved and signer independence unverified; no model has been trained.

---

## Streaming monitor (2026-10-30 19:42)

PID 3392 was **not running** when checked. Its log (`stream_resume2.log`) shows it downloaded and processed 30 more zips
(Adjectives_4of8 to People_5of5, 0 failures, every processed video usable) and then stopped while processing Places_1of4,
with no error (the file's own modified time, 12:18, is stale; the zips on disk date to about 14:24, so it stopped
around then, probably when its session ended). Verified now: **34 of 44 zips processed** (34 part records, 2,969 feature
files); the **other 10 zips are fully downloaded and intact** (sizes match Zenodo: Places 1 to 4, Pronouns 1 to 2, Seasons 1,
Society 1 to 3), so the download is complete and only processing remains; no partial downloads; 36 to 39 GB free. The
interrupted Places_1of4 had a leftover extract folder, which the script clears and redoes (feature file names are
deterministic, so nothing duplicates).

Because the process had already died, I resumed it once (PID 29280, log `stream_resume3.log`, no other instance running)
instead of leaving the dataset stalled. At the 30 s check it had begun processing Places_1of4. A resumed process can stop
with its session; re-running the same command is safe. No manifest exists yet; validation, training and evaluation have not
run and will not until all 44 zips are processed. Observation for later: zips of categories such as Home, Days_and_Time and
Animals contain videos that are not in the authors' split lists (e.g. Home: 49 of 98 videos in Home_1of4); they are skipped, not
used, and the split verifier will report them. The license conflict is still unresolved.

---

## Streaming recovery check (2026-10-30 12:20)

The original streaming process (PID 25032) was **not running**: it stopped with the previous session on 2026-10-29 (no
traceback; the last log lines are a transient download failure, "peer closed connection", for Adjectives_4of8). Verified
state: 4 of 44 zips complete (Electronics_2of2, Adjectives_1of8 to 3of8; 367 feature files = 55 + 3 x 104, matching the four
part records), 6 prefetched zips intact (Pronouns_1of2, Pronouns_2of2, Seasons_1of1, Society_1of3 to 3of3; sizes match Zenodo),
3 incomplete `.part` files (cannot be resumed because Zenodo has no range support; the script overwrites them), `tmp/` empty,
48 to 50 GB free. No manifest (the stale one was renamed earlier). Resume logic inspected in `include_stream.py`: finished zips
are skipped via `_parts/*.csv`, complete zips are reused, partial downloads restart. One new run was started (PID 3392,
logs `stream_resume2.log`); a first attempt via a different launcher exited at once and left nothing running. Because the run is a
child of the session, it may stop again when the session ends; re-running the same command is safe. **Training stays blocked**
while the license conflict is unresolved; nothing else was changed.

---

## Dataset processing check (2026-10-29 23:50)

Process state: the streaming run (`training.include_stream`, PID 25032) is **still running**; no second instance was started.
Completed zips: Electronics_2of2, Adjectives_1of8, Adjectives_2of8 (3 of 44; 104/104 usable videos in each Adjectives zip, 0
failures, 0 unmatched). Adjectives_3of8 was being processed; 6 more zips were prefetched. Free disk 49 GB. No errors in
`stream.log`. The manifest does not exist yet (written at the end), so validation, training and evaluation have **not** been run;
no model exists.

Split mapping: the authors' lists total 4,292 videos (train 3,127, val 348, test 817), exactly the record's video count.
`training/verify_include_split.py` (new, 4 tests) cross-checks lists against processed zips (never-seen videos, videos in two
splits, split mismatches, manifest row count) and exits 2 on any problem; run it before training. Signer IDs are unavailable, so
**the split is predefined and signer independence is unverified**; results must not be called signer-independent.

License (not resolved): the Zenodo record metadata, the creators' own record, says CC BY 4.0 (open access). A third-party
IEEE DataPort page for a derived dataset states the original is CC BY-NC-SA 4.0; the AI4Bharat site gave no statement. I
cannot confirm which is right, so use is restricted to what both allow: non-commercial academic research with attribution (Sridhar
et al., ACM MM 2020), with **no redistribution** of the videos or derived landmark tensors (`data/` is git-ignored). The earlier
"license resolved" wording came from a button label, not from evidence.

Next actions when the run finishes: (1) patch `data/processed/include/dataset_info.json` license text (the running process still
writes the older wording), (2) `verify_include_split`, (3) `validate_dataset`, (4) `train`, (5) `evaluate`.

---

## Dataset download: IN PROGRESS (started 2026-10-29 after your approval)

`training/include_stream.py` is downloading INCLUDE zip by zip, converting to landmark features and deleting videos (see
`DATASET_GUIDE.md`). 1 of 44 zips is done (Electronics_2of2: 55 videos, all usable); the rest is running in the background
with logs at `data/raw/include/stream.log`. Observed speed is roughly 1 to 2 MB/s in total, so expect many hours. **No model
is trained and no metrics exist yet.** When `data/processed/include/manifest.csv` appears: validate, train, evaluate with
the commands in `MODEL_TRAINING.md` (the manifest has the authors' predefined split; signer independence is unverified).
Environment note: Python 3.11 disappeared from the machine and `backend/.venv` was rebuilt on 3.11.15 (via uv); 98 + 3
backend tests pass again.

---

## Phase 14 (final completion audit): complete, 2026-10-29

Classification: **software foundation reached; functional prototype NOT reached; research-ready NOT reached.** Full matrix with
evidence: `docs/PROJECT_COMPLETION_AUDIT.md`. Acceptance run: `scripts\test.ps1` exit 0 (98 pytest, 34 vitest, `tsc`, ESLint,
`next build`), `scripts\dev.ps1` started both servers, live API checks, browser check on Next 16 / React 19, container
build and run, dependency audits clean. Blocked: dataset (license decision, 56.75 GB), model, verified clips, real-camera test.
Unexpected files from another tool appeared in the repo root at 22:38 (see audit section 5); not touched.

---

## Phase 9 (recognition pipeline and real-time infrastructure): complete, 2026-10-29

Re-verified baseline before changes: 70 backend tests, 27 frontend tests, `tsc` clean. Servers from earlier sessions were
no longer running. **Defect found in earlier reporting:** `apiPost` did not surface server `detail` messages (the Phase 7
summary said it did); fixed in `frontend/src/lib/api.ts`.

Changes: bounded buffer with tracking-loss reset (`lib/landmarks.ts`, `useLandmarkCapture.ts`); in-flight guard and
stale-response discard in `WebcamPanel.tsx`; model loaded at startup via `lifespan`; feature-dim/seq_len validation in
`artifacts.py`; recognizer ValueError mapped to 422; `backend/benchmarks/measure.py`; `tests/test_pipeline_audit.py`
(10 tests); 3 new buffer tests. Docs: `EXPERIMENT_PLAN.md` (new), `MODEL_TRAINING.md`.

Results: `pytest` 80 passed; `vitest` 27 passed; lint and `tsc` clean. Latency (one run, n=100 each, i5-13450HX,
Python 3.11.9, localhost, synthetic payloads; `docs/benchmarks/phase9_latency.json`): preprocessing of 60 frames median
9.6 ms; GET /api/health round trip median 6.6 ms; POST /api/landmarks/extract (146 KB) median 56.7 ms, p95 148.6 ms;
Python MediaPipe on a blank frame median 53.2 ms (no person; lower bound only). **Not measured:** browser extraction,
model inference (no model), end to end, frame rate, memory. These are not benchmarks of the full system.

Remaining blockers: no dataset/model; webcam never tested on a real camera; no clips.

---

## Phase 13 (security, deployment, production readiness): complete; **not ready for public deployment**

Dependencies upgraded and verified: Next 14.2.18 to 16.4.3 with React 19.2, R3F 9.8.2, Drei 10.7.9, ESLint 9 flat config,
vitest 5 + vite 7 (`npm audit`: 0 vulnerabilities, from 4 incl. 1 critical, then 6 in dev tooling); FastAPI 0.162 / Starlette
1.10 (`pip-audit`: none, from 14 Starlette advisories); PyTorch 2.5.1 to 2.13.0 (from 6+ advisories). Security fixes: request
body cap (413), `/api/model/status` no longer leaks absolute paths, load-failure details logged not returned, frontend security
headers. Containers: `backend/Dockerfile` (1.48 GB), `frontend/Dockerfile` (460 MB), `docker-compose.yml`, `.dockerignore`;
both images **built and run** (API :18000, web :13000, browser showed "Backend connected" across containers); `docker compose up`
not run (default ports busy). `scripts/setup.ps1` executed end to end (exit 0, idempotent re-run). Full details, hosting
assessment and the list of reasons it is not public-ready: `docs/DEPLOYMENT_READINESS.md`. `pytest` 98 passed, `vitest` 34
passed, `tsc`, ESLint and `next build` clean on the new stack; UI re-verified in the browser (rig self-test, status panel).
No CSP, rate limiting or TLS config; camera under `Permissions-Policy: camera=(self)` not tested on a real camera.

## Phase 12 (avatar and ISL sign animations): infrastructure complete; **sign content BLOCKED (0 clips)**

Audit in `docs/AVATAR_ASSET_AUDIT.md`: no GLB model, procedural 20-bone humanoid, 0 clips, no sign reviewed. Built:
per-sign provenance registry (`backend/config/sign_registry.json`, `app/avatar/sign_registry.py`, `GET /api/avatar/registry`;
status is computed from files and only reaches `verified` with a valid clip, license, attribution, reference, visual review
and signer review); player `stop`, `reset`, `dispose` and 0.2 s blending between signs; rig and imported-skeleton
validation (`lib/avatar/skeleton.ts`); UI shows the original sentence, gloss, per-token status, current token, unsupported
tokens and all controls. Docs: `AVATAR_ASSET_AUDIT.md`, `DEMO_GUIDE.md`.

Verification: `pytest` 95 passed (6 registry tests, shipped-registry consistency); `vitest` 34 passed (7 new player and
skeleton tests); lint and `tsc` clean. **Manual**: a temporary generic arm-raise clip registered under HELLO and WATER was
played in the browser: chips showed "clip not signer-reviewed", FOOD "unsupported: no animation", "Signing HELLO (1 of 2)"
with the current chip highlighted, the avatar raised its arm, and the unregistered clips were flagged. The temporary
clips were then deleted (`animations/` is empty). This verifies the pipeline, **not any ISL sign**.
Not done: GLB import (no asset), reduced-motion handling beyond user-initiated playback, finger-segment articulation.

## Phase 11 (real dataset and training): infrastructure complete; **dataset and model BLOCKED**

Investigated INCLUDE through the Zenodo API (details in `DATASET_GUIDE.md`): CC BY 4.0, open, 56.75 GB, no signer metadata,
authors' train/test split without validation, conflicting third-party license statement. **Nothing was downloaded; waiting
for your decision.** No dataset passed validation, so no model was trained and **no evaluation results exist**;
`backend/models/` is empty.

Built: `training.make_manifest` (labels, signer regex, split file, duplicate hashing, exclusions file), predefined-split
support, class weights, macro precision/recall, duplicate and length reporting in the validator, exclusions written by
`preprocess_videos`, training that refuses unvalidated data, `training.evaluate` (held-out test split, latency).
Fixed: a corrupt checkpoint raised an uncaught pickle/struct error instead of `ModelLoadError` (found by a new test).
Tests: `pytest` 89 passed (9 new in `test_phase11_tools.py`, all synthetic).

## Phase 10 (documentation and IEEE alignment): complete

Created `docs/PROJECT_REPORT.md` (Mermaid architecture, every claim labelled implemented/tested/verified/planned,
Results marked PENDING, placeholders for authors) and `docs/IEEE_PAPER_CHECKLIST.md` (verdict: insufficient evidence for
submission). References [1] MediaPipe, [2] GRU/RNN encoder-decoder, [6] PyTorch were checked via web search results of
their arXiv/NeurIPS pages; [3] INCLUDE via its Zenodo record; [4] ISL-CSLTR via its Mendeley page; [5] CISLR via the ACL
Anthology listing. Author lists for [4]/[5] and paper-internal numbers were not checked. Commands in the README were
checked against existing scripts/modules (the `.ps1` scripts are executed in Phase 13). No target venue chosen, so no
template compliance is claimed.

---

**Current phase: Phase 8 (final verification) complete.** All phases are implemented as working infrastructure.
**Neither direction yields real ISL output**: no dataset is downloaded, no model is trained, and there are no sign
animation clips. Live-webcam extraction was never exercised on a real camera.

## Environment

Windows 11 Home 10.0.26300; Python 3.11.9 venv (3.14.6 is the system default); Node 24.18.0; npm 11.16.0; Git 2.44.0.
Backend: FastAPI 0.115.6, Pydantic 2.10.3, NumPy 2.1.3, PyTorch 2.5.1 (CPU), MediaPipe 0.10.14, OpenCV contrib 4.10.0.84.
Frontend: Next 14.2.18, React 18.3.1, three 0.169.0, R3F 8.17.10, Drei 9.114.3, Tailwind 3.4, Vitest 2.

## Implemented, and how it was verified

| Area | Status | Evidence |
|---|---|---|
| FastAPI app, CORS (explicit origins), `/docs`, `X-Process-Time-Ms` header | Done | pytest; live curl |
| Dashboard, tabs, live status panel (backend, webcam, extractor, model, animations) | Done | vitest; browser |
| Webcam panel, permission/device errors, in-browser MediaPipe load | Done; **real camera never tested** | browser (permission-denied path, extractor init, file loads) |
| Landmark normalization/validation, `POST /api/landmarks/extract` | Done | pytest (9) |
| BiGRU model, artifacts, inference, `GET /api/model/status`, `POST /api/signs/recognize`, training script | Done; **no real model** | pytest with synthetic data only |
| Dataset tools: provenance (ISL-only), validator, video preprocessing, consented recorder | Done; real video and camera recording untested | pytest (blank synthetic video) |
| Translation: labels to gloss, gloss to English, English to gloss, vocabulary endpoint | Done; **placeholder vocabulary** | pytest (15+) |
| Avatar: procedural humanoid, clip format, registry, plan endpoint, sequential player, English to Sign panel | Done; **zero sign clips** | pytest, vitest, browser (rig self-test moved the arm) |
| Sign to English pipeline `POST /api/signs/translate`, Recognize button, latency display | Done; success path only with a synthetic model | pytest integration (8); browser (disabled path) |

## Phase 8 verification (run 2026-10-29)

- `backend\.venv\Scripts\python -m pytest -q`: **70 passed**. `pip check`: no broken requirements.
- Frontend: `npx tsc --noEmit` clean; `npx vitest run` **24 passed** (5 files); `npm run lint` no warnings or
  errors; `npm run build` compiled successfully (static `/`, 98.2 kB first load).
- Live API (backend :8010, frontend :3011): CORS allowed the configured origin, sent no CORS header for
  `http://evil.example`, and a preflight `OPTIONS` for POST returned 200 with the allowed origin and methods.
- Edge cases against the live API: empty text, wordless text, malformed JSON, empty gloss list, empty frames list,
  wrong landmark types and empty avatar plan each returned 422. Recognition with no model returned 503.
  Unknown words (`quantum entanglement`) returned coverage 0.0 with both words unsupported. Unknown gloss `FLY`
  gave empty English with `FLY` unsupported. A `HELLO` avatar plan reported the clip missing and `playable: false`.
  `/api/model/status` reported `not_trained`. OpenAPI lists 10 paths and `/docs` returns 200.
- Browser (earlier phases, same code paths): Sign tab shows Recognize disabled with the no-model message; English tab
  translated "Hello, water please" to HELLO WATER with all glosses "(no animation)".
- **Not verified:** a real webcam in Chrome/Edge; recognition with a real model; any sign animation; mobile layout;
  keyboard-only operation beyond native control semantics; the WebGL-unavailable fallback; `scripts/*.ps1` (syntax
  parsed only, not executed end to end); end-to-end latency with MediaPipe running (only one localhost sample of
  61 ms for translate+plan, not a benchmark).

## Blockers and known limitations

1. **No dataset.** Candidates are researched in `DATASET_GUIDE.md` (INCLUDE, ISL-CSLTR, CISLR). INCLUDE is about
   57 GB, has a reported license conflict (CC BY 4.0 vs CC BY-NC-SA 4.0), and its signer count and split independence
   are unknown. Downloading is your decision.
2. **No sign clips.** Needs ISL signers/linguists; see `AVATAR.md`.
3. **Vocabulary and ordering rules are unvalidated placeholders** (`TRANSLATION.md`).
4. One isolated sign per recognition request; no continuous-sign segmentation; no facial or non-manual features.
5. **`npm audit` (production deps): 4 advisories** (1 critical in `next`, 1 high in its bundled `postcss`, 2 moderate
   in `uuid`/`@react-three/drei`). The `next` fixes require a major upgrade to Next 16, which was not attempted. Not a
   public deployment; do not expose before upgrading. Whether the advisories apply to this local app was not assessed.
6. Hand labels (left/right) are used as MediaPipe reports them, with no mirroring correction.
7. No Git commits were made. Untracked folders `.jetro/` and `.snapshots/` at the repo root and a stray
   `node_modules/` (leftover from an abandoned first attempt in this folder) were not created by this project's code
   and were left untouched; `node_modules/` is git-ignored.
8. Measurements for a paper (accuracy, macro-F1, per-class, confusion matrix, translation coverage, animation
   coverage, end-to-end latency) have **not** been taken, because no real model, test set or clips exist. The
   tooling to record them exists (`metrics.json`, `coverage` field, latency header).

## Next steps

1. Test the webcam path in Chrome/Edge and report any extraction problems.
2. Decide on a dataset (resolve INCLUDE's license, check signers), download it, then run preprocessing, validation
   and training (commands in `README.md`).
3. Commission or record signer-reviewed clips for the vocabulary and add them to `frontend/public/animations`.
4. Replace the placeholder vocabulary with one reviewed by ISL signers; measure translation coverage on a held-out set.
5. Upgrade Next.js before any public deployment.

## Files

See `README.md` for the layout. Key docs: `ARCHITECTURE.md`, `API_REFERENCE.md`, `DATASET_GUIDE.md`,
`MODEL_TRAINING.md`, `TRANSLATION.md`, `AVATAR.md`. Setup, run, test and train commands are in `README.md` and
`scripts/`.
