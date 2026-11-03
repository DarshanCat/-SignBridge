# System Design

## Architecture

SignBridge has three parts: a browser application, a Python backend and a set of files on disk ([[fig:arch]]). The browser extracts landmarks, draws the avatar and holds the user interface. The backend normalizes landmarks, classifies them, segments streams, converts between English and gloss, and serves the clip list. Nothing is stored on the server at run time except takes made with the recorder.

![System architecture of SignBridge. Solid arrows are run-time data flow; dashed arrows show which files each part reads.](figures/diagram_architecture.png){#fig:arch w=6.2}

The main design decisions are the following.

- **Landmarks are extracted in the browser.** Video never leaves the machine. The backend receives arrays of 33 pose and 2 x 21 hand landmarks. Python MediaPipe is used only offline for the dataset, with the same normalization code, so training and inference features match.
- **One preprocessing path.** The normalization, the gap filling and the resampling are the same functions for training, for the REST endpoints and for the WebSocket.
- **Gloss is the shared representation.** The two directions do not share a model. They share only the gloss vocabulary and its dictionary.
- **Missing parts are reported, not hidden.** Without a model the live endpoint answers with an explicit error and closes; without a clip the word is listed as unsigned; without the avatar file a built-in figure is used.
- **Files instead of a database.** The model, the clips, the registries and the recorded takes are files; no database is needed for the prototype.

## Sign to English pipeline

[[fig:s2e]] shows the path from the webcam to an English sentence. In isolated mode the browser sends the newest buffered frames when the user asks for a recognition. In continuous mode it streams chunks of frames every 250 ms and the server segments them before classifying.

![Sign to English pipeline. Continuous mode adds the segmenter in front of the same classifier.](figures/diagram_pipeline_sign_to_english.png){#fig:s2e w=6.4}

The steps are as follows.

1. MediaPipe Holistic returns 33 pose landmarks and 21 landmarks per hand for each video frame.
2. The browser keeps a buffer of the newest 60 frames and drops it after 15 frames without a body pose, so an old partial sign is never mixed with a new one. It rescales the vertical coordinate by the picture aspect (Section 7.9) and sends the frames.
3. The server normalizes each frame: the shoulder midpoint becomes the origin and the shoulder distance the unit, giving 225 values per frame. A missing hand is a block of zeros. Frames without a usable pose are dropped.
4. The sequence is resampled to 32 frames after short hand gaps (three frames or fewer) have been interpolated.
5. The 1D CNN returns a probability for each of the 262 classes. If the top probability is at least the threshold (0.7), the label is accepted; otherwise the answer is UNRECOGNIZED.
6. An accepted label is mapped to its gloss, added to the sequence, and the gloss sequence is turned into an English sentence by rules.

## English to Sign pipeline

[[fig:e2s]] shows the path from typed text to the avatar. The server converts the text to gloss, and the browser plans the playback from the clips that exist.

![English to Sign pipeline. A gloss without a clip is skipped and reported.](figures/diagram_pipeline_english_to_sign.png){#fig:e2s w=6.4}

1. spaCy parses the sentence into tokens, lemmas, tenses and clauses.
2. Rules order the gloss: time signs first, subject and objects in English order, verbs after their objects, negation after the verbs, and question words last. Articles, the copula, auxiliaries and prepositions are dropped and reported with a reason. Unknown words become fingerspelling markers.
3. The dictionary (313 glosses) maps each gloss to a sign entry, and the avatar plan marks which glosses have a clip.
4. The browser fetches and validates the clips and the sequence player blends them with eased transitions while the avatar applies smoothing and a small idle motion.
5. Non-manual markers (negation, yes-no question, WH question) add a rule-based head movement; the words without a clip are listed in the chat.

## Gloss as the shared representation

[[fig:hub]] shows why the two directions can be built and tested separately. Text and signs never meet directly. Text goes to gloss and back by rules; signs go to gloss through the class label of the recognizer and from gloss to clips through the registry. Adding a sign means adding a dictionary entry, a class or a clip, without touching the other direction.

![Gloss is the only thing the two directions share.](figures/diagram_gloss_hub.png){#fig:hub w=6.2}

## Data flow

The live channel is a WebSocket at /ws/predict. The client sends JSON text messages and the server answers with JSON events.

Table: WebSocket messages of the live recognizer. {#tab:ws}
| Direction | Message | Meaning |
|---|---|---|
| server to client | ready | model loaded: number of classes, architecture, threshold and where the threshold came from |
| client to server | predict (frames, commit) | recognize one isolated sign from the frames and optionally add it to the sentence |
| server to client | prediction | accepted or not, label, gloss, confidence, alternatives, number of frames used, gloss sequence and English sentence |
| client to server | frames | continuous mode: a chunk of 1 to 300 frames |
| server to client | sign | one finished sign with its segment and the same fields as a prediction |
| server to client | stream | status of the continuous stream: active, frames seen, sequence, English |
| client to server | undo, reset, flush | remove the last sign, clear everything, close an open sign |
| server to client | error | without a model it sends model_not_trained and closes; other errors name the problem |

The REST endpoints (Appendix B) cover health and status checks, landmark validation, one-shot recognition, translation in both directions, the avatar plan and registry, and the recorder.

## Module design

Table: Backend modules. {#tab:backend}
| Package or file | Responsibility |
|---|---|
| app/main.py, app/core | application, CORS, body size limit, settings read from SIGNBRIDGE_ environment variables |
| app/api | routes: REST, WebSocket, recorder |
| app/recognition | landmark validation and normalization, preprocessing, model definitions, artifact loading, inference, model status, segmenter |
| app/services | live session handling, recognition orchestration, avatar plan |
| app/avatar | clip format and validation, clip registry, sign registry with provenance |
| app/recording.py | quality check, takes on disk, clip building from a take |
| nlp | spaCy text to gloss, gloss to English, dictionary loader, fingerspelling |
| retarget | landmarks to avatar bones, clip builder, vocabulary and promotion tools |
| training | dataset tools, audit, training, comparison, calibration, augmentation, evaluation scripts |

Table: Frontend modules. {#tab:frontend}
| Folder | Responsibility |
|---|---|
| src/app | the single page with five tabs and the footer |
| src/components | panels (conversation, sign to English, English to sign, record, landmark check), the camera hooks, the framing guide and the status panel |
| src/lib | landmark conversion and buffers, MediaPipe loader, overlay drawing, camera request, WebSocket client, recorder, shortcuts, API client |
| src/lib/avatar | clip format, sequence player, Mixamo rig mapping, idle and smoothing layer, non-manual markers, sentence planning, loader |
| src/components/avatar | the 3D viewer, lights, backdrop and the avatar model component |
| public | self-hosted MediaPipe files, avatar model and clips (the last two are git-ignored) |

## Storage

There is no database. [[tab:storage]] lists what is stored and where.

Table: Files used as storage. {#tab:storage}
| Content | Location | In git |
|---|---|---|
| Trained weights, class list, threshold | backend/models | no |
| Sign clips (JSON) | frontend/public/animations | no (see Chapter 10) |
| Avatar model | frontend/public/avatar | no |
| Gloss dictionary, translation rules, sign registry | backend/config | yes |
| Processed INCLUDE features and manifests | data/processed | no |
| Recorded takes (landmarks only) | data/recorded | no |
| Evaluation results | docs/evaluation | yes |

## Application programming interface

The API is described in Appendix B. Every response carries an X-Process-Time-Ms header with the server time, requests with a body above 2 MB are refused with status 413, and the recorder endpoints answer 403 when recording is disabled by configuration.
