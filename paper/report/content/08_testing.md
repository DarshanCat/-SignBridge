# Testing

## Test strategy

Testing has four layers: automated unit and integration tests, a benchmark of the complete browser path, end-to-end runs in a real browser with a fake camera, and manual inspection. The automated tests use tiny synthetic models and synthetic landmarks, so their scores are never reported as results. They check the mechanics of the code. The measured results of the project come from the evaluation scripts (Chapter 9).

## Automated tests

The test script runs the backend tests with pytest, the TypeScript compiler, ESLint, the frontend tests with Vitest and the production build. On the current repository head the backend suite has 367 tests and the frontend suite has 104 tests, and all of them pass; the TypeScript compiler, ESLint and the production build are clean.

Table: Automated test suites. {#tab:tests}
| Suite | Tests | What it covers |
|---|---|---|
| Backend (pytest) | 367 in 31 files | landmark normalization, preprocessing, models, training pipeline, inference, API, WebSocket, recorder, retargeting, text to gloss, gloss to English, registry, data tools, deployment switches, augmentation, checkpoint and resume |
| Frontend (Vitest) | 104 in 21 files | landmark conversion and buffers, camera request and fallback, overlay and framing warning, WebSocket client, recorder, shortcuts, avatar player, rig mapping, idle and smoothing layer, non-manual markers, sentence planning, status logic, deployment switches |
| Type check, lint, production build | pass | the whole frontend |

Table: The largest backend test files. {#tab:backendtests}
| File | Tests | Subject |
|---|---|---|
| test_nlp.py | 80 | text to gloss rules: 36 English to gloss pairs, 20 gloss to English pairs, 8 round trips and edge cases |
| test_gloss_to_text_quality.py | 43 | 40 gloss sequences for the English generator and its quality rules |
| test_slr_pipeline.py | 24 | recognition pipeline, preprocessing and models on synthetic data |
| test_retarget.py | 16 | landmarks to bones with forward kinematics, mirror test, clip validity |
| test_translation.py | 15 | vocabulary and translation endpoints |
| test_training_pipeline.py | 15 | training, resume, checkpoints, splitting, metrics |
| test_record_session.py | 14 | guided sessions, plan, resume counts, quality check |
| test_clips.py | 12 | clip format validation and the avatar plan |

Specific properties that are tested include: the live and offline preprocessing agree to 1e-6; the vectorized resampling equals the per-column interpolation to 1e-6; the vertical-scale augmentation equals re-normalizing scaled raw landmarks; a training run resumed from a checkpoint ends with the same weights as an uninterrupted run; the recorder endpoints answer 403 when disabled and write nothing; a WebSocket from a foreign origin is refused when the origin check is on; and an unsupported or missing model never produces a prediction.

## Integration tests

Integration tests drive the real API with the test client: the REST endpoints end to end, the WebSocket with isolated and continuous messages, and the recorder with synthetic takes. In addition, 80 real INCLUDE test samples were rebuilt into landmark frames and sent through the live socket; all 80 gave exactly the offline model's labels and confidences (identical within 1e-4).

## Browser-path benchmark

The benchmark feeds INCLUDE videos frame by frame through the real in-browser MediaPipe Holistic of the prototype and classifies the result with the live code path. It is described in Section 9.3 and its limits are stated there. It uses frame stepping instead of a looping fake camera because headless Chrome extracts only about 6 frames per second and a live fake camera would drop frames and mix capture starvation into the error rate. The extracted landmark files of the larger corpora (211 validation and 312 test videos, two framings) were validated for readability, shape, finite values, duplicates and completeness before use.

## End-to-end tests with a fake camera

Real Chrome was driven by Playwright with a fake camera that plays a converted INCLUDE test video. The first run used letterboxed 4:3 pictures of three test videos (Hat, Doctor, Yesterday), before the picture aspect rescale existed.

Table: End-to-end test with a fake camera before and after the aspect rescale (isolated and continuous modes, one run each). {#tab:fake}
| Video | Before the rescale | After the rescale |
|---|---|---|
| Hat | recognized correctly | recognized correctly (99.6 percent isolated; HAT in continuous mode) |
| Doctor | a skirt sign | DOCTOR (95 percent) in continuous mode, but unrecognized when isolated and two SLOW detections in continuous mode |
| Yesterday | THEY | unrecognized (best guess Cell phone, 56 percent) |

These three runs are a smoke test, not a measurement. They exposed the picture aspect problem and led to the benchmark of 100 videos. The guided session also rejected a take with only 18 frames with a clear reason, as designed. The same fake camera, with the head hidden, produced the screenshots of this report.

## Manual verification

The production build was inspected in a browser: all five tabs, the landmark overlay, the camera resolution line, the framing guide, the avatar at rest and mid-sign, the chat in both directions and the footer notices. The layout was checked down to a 375 pixel wide screen.

## What testing does not show

No test used a real webcam with a real signer. The automated tests use synthetic models and landmarks, the benchmark uses dataset videos re-encoded as pictures, and the fake-camera runs use three videos. No clip and no text rule has been checked by an ISL signer, so the tests prove consistency, not linguistic correctness.
