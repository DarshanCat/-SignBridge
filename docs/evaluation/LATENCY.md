# Latency and frame rate of the live path

Measured on 13th Gen Intel(R) Core(TM) i5-13450HX, 16 logical CPUs, 16.8 GB RAM, win32 10.0.26300; Chrome (headless) 156.0.0.0; model: cnn, 262 classes, 343558 parameters. Frames are real INCLUDE sign video frames resized to 640x480 (a webcam size); the API ran on the same machine, so the WebSocket numbers have no network distance. Headless Chrome with software or default GPU settings is not a real user's browser: the extraction numbers are for this machine and setup, not a promise for another one. No camera was involved, and no recognition accuracy is measured here (validation sequences only for the model timing, the test split is not read).

## What each stage costs

| Stage | Median (95th percentile) | Where measured |
|---|---|---|
| Landmark extraction, MediaPipe Holistic in the browser, CPU delegate (the app's default) | 149 ms (178) per frame | `tools/latency/measure.js` |
| Same with the GPU delegate requested | 124 ms (180) per frame | `MP_DELEGATE=gpu` |
| Decoding and drawing the test frame (not part of the app) | 2.8 ms | harness only |
| WebSocket round trip with an empty message (reset) | 0.7 ms (2.0) | real `/ws/predict` |
| One streamed chunk of 8 frames (28 KB) to the server's reply | 1.7 ms (11.1) | real `/ws/predict`, continuous mode |
| Whole sign in one `predict` message (265.4 KB, 77 to 80 frames) to the prediction | 33.6 ms (201.3) | real `/ws/predict`, includes parsing, preprocessing and the model |
| Preprocessing one sequence (gap fill, resample to 32 frames) | 0.88 ms (1.15) | `tools/latency/model_latency.py` |
| Model forward pass, one sequence, batch 1, 10 torch threads | 13.1 ms (29.7) | 347 validation sequences |
| MediaPipe start-up (script, model download, first frame) | 1.3 s (CPU), 10.9 s (GPU requested) | once per page load |
| WebSocket connect to the server's ready message | 165 ms | once per session |

## Frame rate

- Sustained extraction rate with one frame in flight (what the capture loop reaches when the camera is faster): **6.7 frames per second** with the CPU delegate, 8 with the GPU delegate requested. A 30 fps webcam is therefore sampled at about a quarter of its rate.
- The training features use every second frame of INCLUDE videos (stride 2). The three test videos have 77 to 80 frames; if a camera delivered such a sign at 30 fps (an assumption, the files' frame rate was not read) it would last about 2.6 s and give about 18 extracted frames at this rate, against about 39 at stride 2. The recognizer resamples every sign to 32 frames, so a sparse capture is stretched, not rejected. Whether the lower live rate costs accuracy was not measured here.
- The server side is not the bottleneck: the model and the WebSocket together need a few tens of milliseconds per sign, the browser extraction needs about 150 ms per frame.

## Limits of this measurement

- One machine, headless Chrome, local server, 640x480 input, three sign videos; no camera capture time, no rendering of the page, no network.
- The GPU run only requested the GPU delegate; I did not verify that the GPU was actually used. It was 16 percent faster per frame here and took longer to start.
- The delay a user sees also includes the time the sign takes and the pause the segmenter waits for before it closes a sign; these are not measured here.
