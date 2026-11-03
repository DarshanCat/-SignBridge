# Requirements

## Hardware requirements

The system was developed and measured on one machine, so the numbers in this report describe that machine.

Table: Hardware used and hardware required. {#tab:hw}
| Item | Development machine | Minimum for running the prototype |
|---|---|---|
| Processor | Intel Core i5-13450HX, 16 logical processors | A recent multi-core CPU; no GPU is required |
| Memory | Not a limiting factor | Enough for a Python process with PyTorch and spaCy, and a browser |
| Camera | 640x480 and 1280x720 sources, real and fake | A webcam; 1280x720 is requested and any size is accepted |
| Graphics | Software WebGL in headless tests, a GPU in normal use | WebGL 1 or 2 for the 3D avatar; a built-in figure is used if the avatar file is missing |
| Disk | Several gigabytes for the INCLUDE archives and features | Small for running (model about 1.4 MB); large only for training |
| Operating system | Windows 11 | Windows for the provided scripts; the code is portable |

Model inference takes about 0.4 ms per sign on the development CPU (median of 200 runs), so network and landmark extraction dominate the delay.

## Software requirements

Table: Software and library versions. {#tab:sw}
| Layer | Software | Version or note |
|---|---|---|
| Runtime | Python | 3.11 |
| Runtime | Node.js | 20 or newer (22 in the container build) |
| Version control | Git | any recent version |
| Backend | FastAPI, Uvicorn, Pydantic, pydantic-settings, Starlette | 0.162.0, 0.32.1, 2.10.3, 2.6.1, 1.10.0 |
| Backend | NumPy, PyTorch (CPU build) | 2.1.3, 2.13.0 |
| Backend | spaCy with en_core_web_sm | 3.8.7 with 3.8.0 |
| Data processing | MediaPipe (Python), OpenCV | 0.10.14, 4.10.0.84 |
| Frontend | Next.js, React, TypeScript, Tailwind CSS | 16, 19, TypeScript, Tailwind |
| Frontend | React Three Fiber, drei, three | 9.8, 10.7, 0.169 |
| Frontend | MediaPipe Holistic (WebAssembly), self-hosted | 0.5.1675471629 |
| Testing | pytest, Vitest, ESLint, TypeScript compiler | as installed by the setup script |
| Browser | A current Chrome or Edge | camera and WebGL permissions |
| Optional | Docker Desktop | to build the Hugging Face Space image |

## Functional requirements

- **FR1.** Read the webcam in the browser and extract pose and hand landmarks without sending video to any server.
- **FR2.** Recognize one isolated ISL sign from a buffer of landmarks and return the label, the confidence and the alternatives.
- **FR3.** Return UNRECOGNIZED instead of a label when the confidence is below the threshold chosen on validation data.
- **FR4.** Recognize signs in a continuous stream by finding where each sign starts and ends, and build a gloss sequence and an English sentence with undo and clear.
- **FR5.** Convert typed English to an ISL gloss sequence with non-manual marker tags, and list the words that cannot be signed.
- **FR6.** Play one clip per gloss on a 3D avatar with smooth transitions, speed control, pause and replay.
- **FR7.** Offer a conversation view with a chat log for both directions.
- **FR8.** Record new signs and signer-labelled takes as landmarks only, with a quality check and clear reasons for rejection.
- **FR9.** Compare the browser landmarks with Python MediaPipe landmarks on the same recording.
- **FR10.** Show the state of every component (backend, camera, landmark extraction, model, clips) from real checks.
- **FR11.** Guide the user to a good camera framing and warn when the person is too small in the picture.
- **FR12.** Allow a deployment in which recording is disabled and the notices about data, licence and review are always shown.

## Non-functional requirements

- **Privacy.** Video never leaves the browser. Only landmark arrays are sent, and the public deployment stores nothing.
- **Honesty.** The system never invents a prediction, a metric or a clip. Missing models, clips and words are reported.
- **Performance.** Model inference in milliseconds; the production build loads the page in 0.25 s against 0.9 s in development mode, measured on the development machine.
- **Reliability.** Every stage reports what it could not do (no model: 503; unusable landmarks: 422; unsupported words; missing clips; unreachable backend: a banner).
- **Reproducibility.** The same preprocessing function serves training and inference; training is seeded and can resume from checkpoints; results are produced by scripts.
- **Usability and accessibility.** Keyboard shortcuts for the main actions, touch targets of at least 44 pixels and a layout that works down to a 375 pixel wide screen.
- **Portability and deployment.** A production build served locally with one script, and prepared (not performed) deployments on Vercel and Hugging Face Spaces.
- **Licence compliance.** INCLUDE-derived material is handled under the stricter CC BY-NC-SA 4.0 reading and kept out of the public repository.
- **Testability.** Automated tests for the backend and the frontend, and a benchmark of the browser path.
