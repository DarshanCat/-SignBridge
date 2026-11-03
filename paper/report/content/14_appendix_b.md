# Appendix B: API Reference

The interactive documentation is served by the backend at /docs. Every response carries an X-Process-Time-Ms header, and requests with a body above 2 MB are refused with status 413.

Table: REST and WebSocket endpoints. {#tab:api}
| Endpoint | Purpose |
|---|---|
| GET /api/health | status, service name and version |
| GET /api/model/status | state of the recognition model: not trained, loaded or error |
| GET /api/avatar/animations | the valid clip files and any invalid ones |
| GET /api/avatar/registry | per-sign provenance and computed status (no clip, clip unreviewed, verified, missing asset) and totals |
| POST /api/nlp/text-to-gloss | text of 1 to 500 characters to gloss, tokens with fingerspelling letters, non-manual markers, tense and dropped words with reasons |
| POST /api/nlp/gloss-to-text | gloss list to English by heuristic rules |
| POST /api/translation/english-to-gloss | English to gloss with per-word status, unsupported words and coverage |
| POST /api/translation/gloss-to-english | gloss list (1 to 50) to English with unsupported tokens |
| GET /api/translation/vocabulary | glosses, English meanings and whether each has a clip |
| POST /api/avatar/plan | per-token availability and clip address for a gloss list |
| POST /api/landmarks/extract | validate and normalize 1 to 300 landmark frames and report usability and warnings |
| POST /api/signs/recognize | predictions for one isolated sign from landmark frames; 503 without a model, 422 for unusable landmarks |
| POST /api/signs/translate | recognition, confidence threshold, label to gloss and English for one isolated sign |
| WS /ws/predict | live recognition: isolated and continuous modes (messages in Chapter 5) |
| POST /api/record/sign | store a landmark take after a quality check, optionally with a clip; 403 when recording is disabled |
| GET /api/record/plan | the glosses of a guided session, priority words first |
| GET /api/record/takes | saved takes per gloss for one signer, so that a session can resume |

Table: Configuration through environment variables (prefix SIGNBRIDGE_). {#tab:config}
| Variable | Meaning |
|---|---|
| CORS_ORIGINS | JSON list of allowed web origins |
| CORS_ORIGIN_REGEX | one regular expression for further origins, for example preview deployments |
| WS_CHECK_ORIGIN | refuse WebSocket connections from origins that CORS would refuse |
| RECORDING_ENABLED | turn the recorder endpoints on or off |
| MODEL_DIR, ANIMATION_DIR | where the model and the clips are read |
| MIN_CONFIDENCE | default confidence threshold when the model has none |
| MAX_BODY_BYTES | request body limit |
