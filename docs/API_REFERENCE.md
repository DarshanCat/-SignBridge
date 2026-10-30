# API reference

Interactive docs: `/docs` (Swagger) on the backend.

| Endpoint | Status |
|---|---|
| `GET /api/health` | Implemented. Returns `{status, service, version}`. |
| `GET /api/model/status` | Implemented. `state` is `not_trained`, `loaded` or `error`. |
| `GET /api/avatar/animations` | Implemented. Lists valid `*.json` clips in `frontend/public/animations` (format in `AVATAR.md`) and reports invalid files in `invalid`. |
| `GET /api/avatar/registry` | Implemented. Per-sign provenance and computed status (`no_clip`, `clip_unreviewed`, `verified`, `missing_asset`), unregistered clips, totals. 503 if the registry file is invalid. |
| `GET /api/translation/vocabulary` | Implemented. Glosses, English, and whether each has an animation clip. |
| `POST /api/landmarks/extract` | Implemented. Body `{frames: [{pose, left_hand, right_hand}]}` (1 to 300 frames; 33/21/21 points of x,y,z, parts nullable). Returns normalized `features` (225 per frame), per-frame reports, `usable` and `warnings`. 422 on malformed input. |
| `POST /api/signs/recognize` | Implemented. Same body as landmarks/extract. 503 if no trained model, 422 if the sequence is unusable, else `{predictions:[{label,confidence}], num_frames_used}` from the model. |
| `POST /api/signs/translate` | Implemented. Same body as `recognize`. Runs model, confidence threshold (`SIGNBRIDGE_MIN_CONFIDENCE`, default 0.5), label to gloss, gloss to English for ONE isolated sign. Returns `{predictions, num_frames_used, accepted, min_confidence, gloss, english, unsupported, message}`. 503 with no model or invalid vocabulary, 422 for unusable landmarks. |
| `POST /api/translation/gloss-to-english` | Implemented. Body `{gloss: [..]}` (1 to 50). Returns `{english, gloss, unsupported, note}`. Rule-based; see `TRANSLATION.md`. |
| `POST /api/translation/english-to-gloss` | Implemented. Body `{text}` (1 to 500 chars). Returns `{gloss, words[{word,gloss,status}], unsupported, coverage, note}`. 422 if no words, 503 if the vocabulary file is invalid. |
| `POST /api/avatar/plan` | Implemented. Body `{gloss: [..]}`. Returns per-token `{gloss, available, clip_url}`, `missing`, `playable`, `message`. |

Every response carries an `X-Process-Time-Ms` header (server-side time).

Requests with a `Content-Length` above `SIGNBRIDGE_MAX_BODY_BYTES` (default 2 MB) get 413.
