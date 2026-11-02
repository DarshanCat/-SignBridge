# API reference

Interactive docs: `/docs` (Swagger) on the backend.

| Endpoint | Status |
|---|---|
| `GET /api/health` | Implemented. Returns `{status, service, version}`. |
| `GET /api/model/status` | Implemented. `state` is `not_trained`, `loaded` or `error`. |
| `GET /api/avatar/animations` | Implemented. Lists valid `*.json` clips in `frontend/public/animations` (format in `AVATAR.md`) and reports invalid files in `invalid`. |
| `POST /api/nlp/text-to-gloss` | Implemented (spaCy rules, `docs/NLP.md`). Body `{text}` (1 to 500 chars). Returns gloss, tokens (with fingerspelling letters), non manual markers, tense, dropped words with reasons, note. 422 for wordless text, 503 if the spaCy model or dictionary is missing. |
| `POST /api/nlp/gloss-to-text` | Implemented. Body `{gloss: [..]}`. Returns English reconstructed by heuristic rules. |
| `WS /ws/predict` | Live isolated sign recognition. Without a trained model: sends `{type: error, error: model_not_trained}` and closes with code 1013 (never a prediction). With a model: sends `{type: ready, classes, architecture, threshold, threshold_source}`; the client then sends `{type: predict, frames: [...], commit: true}` (1 to 300 landmark frames, same shape as `landmarks/extract`) and receives `{type: prediction, accepted, label, gloss, confidence, threshold, alternatives, sequence, english, num_frames_used}`; `label` is `UNRECOGNIZED` below the threshold and the sentence is unchanged. `{type: reset}` clears the sentence (`reset_ok`). Errors (`bad_message`, `bad_frames`, `unusable_sequence`, `too_large`) keep the connection open. Same preprocessing as training. |
| `WS /ws/predict` continuous mode | Client sends `{type: frames, frames: [...]}` in chunks (1 to 300 frames each, about every 250 ms). The server segments the stream and returns one `{type: sign, accepted, label, gloss, confidence, alternatives, segment: {start, end, frames}, sequence, english}` per finished sign (`label` is `UNRECOGNIZED` below the threshold and the sentence is unchanged), followed by `{type: stream, active, frames_seen, usable_frames, sequence, english}` for every chunk. `{type: undo}` answers `{type: sequence, removed, sequence, english}`; `{type: reset}` clears the sentence and the segmenter; `{type: flush}` closes a sign still open. Segmenter settings: `backend/app/recognition/segmenter.py`. |
| `POST /api/record/sign` | Implemented. Body `{gloss, fps, frames, signer_id?, make_clip?}` (landmarks only, no video). Checks quality (at least 20 frames, fps 5 to 60, body missing in at most 10 percent and no hand in at most 30 percent of frames, and the live segmenter must find a sign in the take); a rejected take is not stored and the reasons are returned. An accepted take is saved under `data/recorded/<GLOSS>/` or, with `signer_id` (guided sessions), `data/recorded/<SIGNER>/<GLOSS>/` (features and metadata, plus an unreviewed `self-recorded` clip unless `make_clip` is false). 422 for an invalid gloss or signer ID. |
| `GET /api/record/plan` | Implemented. The glosses a guided session records: the 50 grammar words of the dictionary that are not INCLUDE classes, priority words (WHERE, GO, LIKE, NOT, HELP, WHAT, YES, NO) first. |
| `GET /api/record/takes?signer_id=P01` | Implemented. Saved takes per gloss for one signer, so a stopped session resumes: `{signer_id, counts, total}`. |
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
