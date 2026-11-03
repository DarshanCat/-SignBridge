# Implementation

## Recognition models

Three architectures are implemented behind one model builder and trained with identical settings.

Table: The three recognition models. {#tab:models}
| Model | Structure | Parameters |
|---|---|---|
| 1D CNN | three Conv1d blocks (kernel sizes 5, 5 and 3, 128 channels, batch normalization, ReLU) over time, global mean and max pooling, dropout, linear head | {{j:seed0_model_metrics.json:baseline_cnn.parameters:,}} |
| BiGRU | two-layer bidirectional GRU (hidden size 128), mean over time, dropout, linear head | {{j:seed0_model_metrics.json:baseline_bigru.parameters:,}} |
| Transformer | linear projection to 128, learned positional embedding, two self-attention encoder layers (4 heads, feed-forward size 256), layer norm, mean pooling, linear head | {{j:seed0_model_metrics.json:baseline_transformer.parameters:,}} |

The training settings are the same for all three: at most 60 epochs, patience 10 on the validation macro-F1, batch size 16, Adam with learning rate 0.001, hidden size 128, two layers (four heads for the Transformer), dropout 0.3, sequence length 32, hand-gap interpolation of three frames, seed 0. Every batch also receives Gaussian noise of standard deviation 0.01 on all 225 input values; the values are in shoulder widths, so this is about 0.0013 of the picture width at the median INCLUDE shoulder width of 0.133. Model selection and early stopping use the validation split only, and each model is evaluated on the test split once. The training pipeline refuses to train on a dataset that has not passed validation.

## Training pipeline, augmentation and checkpoints

The training code is separate from the API; the API only loads the artifacts (weights, class list, threshold). Two additions were made for the deployment study.

- **Deployment augmentation** (`training/augment.py`): a vertical scale drawn from 0.85 to 1.20 (applied to 80 percent of samples and exact: the coordinates are re-normalized with the new shoulder distance, tested against re-normalizing scaled raw landmarks), landmark noise on x and y of detected landmarks with a per-sample standard deviation of up to 0.01 of the picture size, and hand dropout with a per-sample probability of up to 0.2 per frame and hand. Missing hands stay exactly zero.
- **Checkpoints and resume**: the training writes the last and the best state after every epoch (atomically) and can resume with the same settings; a run resumed after a stop ends with the same weights as an uninterrupted run (tested).

The resampling function was vectorized (about 30 times faster, identical values to 1e-6, tested), which made training with augmentation practical.

## Live recognition and the threshold

The server loads the model once at start. A prediction below the threshold is returned as UNRECOGNIZED and leaves the sentence unchanged. The threshold is the lowest value of 0, 0.3, 0.5, 0.7, 0.8, 0.9 and 0.95 that gives at least 95 percent accuracy on the answered validation samples of the best model; for the 1D CNN this is 0.7 (validation coverage 0.8818, accuracy on answered 0.9608). It is stored with the model and sent to the client in the ready message together with its source. Through the live socket, 80 real test samples rebuilt into landmark frames gave exactly the offline model's labels and confidences.

## Continuous signing

The segmenter (`app/recognition/segmenter.py`) works on the normalized feature rows. A frame is engaged when a wrist is above the rest line (2.0 shoulder widths below the shoulder midpoint; resting hands sit at about 2.8) and the wrists moved in the last 10 frames. A sign opens after 2 engaged frames and closes after 6 rest frames, where hands that are raised but still for 10 frames also count as rest. The segment keeps 5 frames before and 4 after, because the training samples begin and end with the hands down, and segments with fewer than 6 engaged frames are dropped as noise. Each segment is classified by the same model and threshold. The parameters were tuned on validation streams and then run once on test streams (Section 9.5). Signs signed back to back without a pause cannot be separated by this method.

## Text to gloss

The rule layer (`backend/nlp`) uses spaCy 3.8.7 with the small English model. For each clause it outputs, in order: time signs, subject and other content in English order (a possessive uses the pronoun sign, so "my brother" gives I BROTHER), verbs after their objects and lemmatized (went becomes GO), NOT after the verbs, modals, and question words last. It drops and reports articles, the copula and auxiliaries, prepositions, the infinitive "to", "and", punctuation and intensifiers. A word that is not in the dictionary becomes a fingerspelling token such as FS:RAVI; no fingerspelling clips exist. Tags for negation, yes-no questions and WH questions drive a head movement of the avatar. The dictionary has 313 entries: the 263 INCLUDE class names and 50 grammar words that INCLUDE lacks. **These rules are simplified assumptions that no ISL signer or linguist has validated**; the tests document the rules and are not linguistic ground truth.

## Gloss to English

The reverse direction is a heuristic: it reverses the order, inserts articles, the copula and auxiliaries, adds "to the" after motion verbs and place nouns, conjugates verbs from time signs (past after YESTERDAY or BEFORE, future after TOMORROW or NEXT, otherwise present), turns "pronoun NAME name" into "My name is X", and writes fingerspelled tokens as names. It has a small verb list, no plural handling and inserts "the" heuristically. Forty tested gloss sequences cover cases such as was, were, will be, on Monday, in the morning, possessives and greetings.

## Retargeting landmarks to avatar clips

Clips are produced from INCLUDE landmark samples (`backend/retarget`). For each frame the converter computes the shoulder and elbow direction, the forearm direction, the hand orientation (wrist to middle knuckle and index to pinky knuckle) and one curl angle per finger. It then smooths the result, handles hand dropout (hold briefly, then relax to rest) and adds a 0.25 second ramp from and to the rest pose. Sixteen unit tests check the retargeter with forward kinematics under the same Euler convention as the avatar, including a left and right mirror test. Known limits are that the roll of the upper arm and forearm is not recovered, finger spread and thumb opposition are not modelled, and the depth coordinate is noisy. Each clip is registered with its provenance, and the registry cannot mark a sign verified without a recorded human review. **All 262 clips are automatic retargets of one training sample each and none is reviewed by a signer.**

## The avatar

The avatar is a Mixamo character loaded as a GLB file and driven by SignBridge clips. The rig mapping derives the arms-down pose from the loaded skeleton (not assumed), spreads the finger curl over the three joints of each finger, and rests bones without a clip track in that pose. Playback is by a sequence player: clips run back to back with 0.25 second eased transitions (smoothstep weights and quaternion slerp for body bones), speed control, pause, replay and restart. A presentation layer sits between the player and the skeleton. It adds a very small breathing, weight shift and head drift; relaxes an arm that hangs at rest (slight angle out, elbow bend, softly curled and fanned fingers) and fades that out completely as soon as the arm is lifted, so a sign is played as it was retargeted; and smooths the final pose over a time constant of 0.07 seconds so that nothing snaps at the start of a sentence, between clips or at the end. The scene has three-point lighting, a gradient backdrop and a camera framed on the upper body. [[fig:avatar]] shows the avatar across one sentence. If the GLB file is missing, a built-in procedural figure is used.

![The avatar across the sentence "Hello. Thank you. Good morning. Doctor." at half speed, eight frames from the production build. The avatar is a mannequin; its face is not animated, and no clip is reviewed by a signer.](figures/avatar_frames_sentence.png){#fig:avatar w=6.4}

## Frontend and user interface

The frontend is a Next.js 16 application with five tabs and a footer that carries the notices about research status, unreviewed clips, the INCLUDE attribution, the CC BY-NC-SA 4.0 non-commercial licence and the fact that video stays in the browser. The screenshots below were taken from the production build with a fake camera that plays an INCLUDE test video whose head is hidden by a mosaic, so that no face appears. The recognized sign shown in [[fig:sign]] is the one the video shows.

- **Conversation** ([[fig:conv]]): one chat log for both directions. Recognized signs build a sentence that is sent as a message by a button, by a key, or after 3 seconds of rest. Typed messages are converted to gloss, signed by the avatar and kept in the chat with a line stating which words had no clip.
- **Sign to English** ([[fig:sign]]): the camera with the landmark overlay and the framing guide, the buffer counters, isolated recognition on request and a continuous mode.
- **English to Sign** ([[fig:e2sshot]]): the gloss with the status of each clip, the avatar mid-sign, and playback controls. The supported vocabulary below the avatar lists which glosses have a clip.
- **Record sign** ([[fig:rec]]): a single-sign mode and a guided session (Section 7.11).
- **Landmark check** ([[fig:check]]): records 4 seconds of video with the browser landmarks so that Python MediaPipe can be compared offline.

![Conversation tab: a signed message, a typed message that the avatar is signing, the camera with its overlay and the system status. The camera feed is an INCLUDE test video with the head masked.](figures/screenshot_conversation.png){#fig:conv w=5.0}

![Sign to English tab with the fake camera: landmark overlay, the dashed framing guide, the buffer counters and an isolated recognition result.](figures/screenshot_sign_to_english.png){#fig:sign w=5.0}

![English to Sign tab: the gloss of "Hello, thank you", the avatar in the middle of the sign HELLO and the playback controls. The page continues with the vocabulary list.](figures/screenshot_english_to_sign.png){#fig:e2sshot w=5.2}

![Record sign tab (single sign mode) with the camera running. Nothing is recorded until the user presses the record button.](figures/screenshot_record_sign.png){#fig:rec w=5.0}

![Landmark check tab with the camera running. It records a short video and the browser landmarks locally for the offline comparison.](figures/screenshot_landmark_check.png){#fig:check w=5.0}

The camera is requested at 1280 x 720 (an ideal constraint, so the nearest size is used) with a fall back to whatever the camera gives, and the real resolution is shown. MediaPipe returns x as a fraction of the picture width and y as a fraction of its height, and the dataset videos are 16:9, so a 4:3 picture gives vertical distances that are smaller by 0.75 after normalization. The browser therefore multiplies every vertical coordinate by (16/9) divided by the picture aspect (4/3 for a 4:3 camera) before it is sent. The framing guide draws the head, shoulders and hands at a shoulder width of about 14 percent of the picture width, inside the tested range, and the app warns when the smoothed shoulder width falls below 0.10 (Section 9.3).

## Backend

The backend is a FastAPI application. Settings are read from SIGNBRIDGE_ environment variables: the allowed web origins (and a pattern for preview deployments), a switch that makes the WebSocket check the origin, a switch that turns the recorder off, and the model and clip folders. The body size is limited to 2 MB. The WebSocket handler keeps one session per connection with the sentence and the segmenter state. Startup loads the model and preloads spaCy, and the model status endpoint reports not trained, loaded or error without ever substituting a prediction.

## Recorder

The recorder collects landmarks only, never video. In single mode the user records a sign that INCLUDE lacks after a 3-2-1 countdown. In guided mode the user enters a signer identifier, the number of takes per sign and a list of signs (the 50 grammar words are preloaded, with WHERE, GO, LIKE, NOT, HELP, WHAT, YES and NO first); the session shows one sign at a time, counts only accepted takes, explains rejected ones and resumes for the same identifier. A take is accepted when it has at least 20 frames, a frame rate of 5 to 60 per second, a body in at least 90 percent of the frames, a hand in at least 70 percent, and the segmenter finds a sign in it. Takes are stored as landmark arrays under the signer and the sign, and a promotion tool turns a good single take into a clip. The signer roles for the self-recorded data are fixed in advance (training S01 to S03, validation S04, test S05), and a builder produces a combined manifest with a signer-level split.

## Deployment

A production build is served locally with one script. Two deployments are prepared and tested locally but were not performed: the web application on Vercel and the API in a Docker container for Hugging Face Spaces. The container uses CPU PyTorch without MediaPipe or OpenCV, runs as an unprivileged user on port 7860 and downloads the weights and clips at start from a private repository, so that they are never in the image or in git. It was built and run locally (about 1.6 GB on disk), and health, the CORS header for an allowed origin, a correct prediction through the WebSocket, a refused foreign origin and a disabled recorder were checked. In the public configuration the recorder tab is hidden and the API refuses recording. The step-by-step instructions are in `docs/DEPLOYMENT.md`. Section 10.2 lists the problems that were found in later commits connected with the Vercel deployment, one of which has been fixed.
