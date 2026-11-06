"""docs/evaluation/LATENCY.md from latency_browser_ws.json (CPU delegate), latency_browser_ws_gpu.json and latency_model.json. Nothing is typed in.
usage (repository root):  python -I tools/latency/report.py"""
import json
from pathlib import Path

EV = Path(__file__).resolve().parents[2] / "docs" / "evaluation"
c = json.loads((EV / "latency_browser_ws.json").read_text(encoding="utf-8"))
g = json.loads((EV / "latency_browser_ws_gpu.json").read_text(encoding="utf-8"))
m = json.loads((EV / "latency_model.json").read_text(encoding="utf-8"))
f = lambda d: f"{d['median']:.1f} ms (95th percentile {d['p95']:.1f}, max {d['max']:.1f}, n = {d['n']})"
o = []
P = o.append
P("# Latency and frame rate of the live path\n")
P(f"Measured on {c['machine']['cpu']}, {c['machine']['logical_cpus']} logical CPUs, {c['machine']['ram_gb']} GB RAM, {c['machine']['platform']}; "
  f"Chrome (headless) {c['chrome'].split('HeadlessChrome/')[1].split(' ')[0]}; model: {m['model']['arch']}, {m['model']['classes']} classes, {m['model']['parameters']} parameters. "
  "Frames are real INCLUDE sign video frames resized to 640x480 (a webcam size); the API ran on the same machine, so the WebSocket numbers have no network distance. "
  "Headless Chrome with software or default GPU settings is not a real user's browser: the extraction numbers are for this machine and setup, not a promise for another one. "
  "No camera was involved, and no recognition accuracy is measured here (validation sequences only for the model timing, the test split is not read).\n")
P("## What each stage costs\n")
P("| Stage | Median (95th percentile) | Where measured |")
P("|---|---|---|")
P(f"| Landmark extraction, MediaPipe Holistic in the browser, CPU delegate (the app's default) | {c['extraction_ms_per_frame']['median']:.0f} ms ({c['extraction_ms_per_frame']['p95']:.0f}) per frame | `tools/latency/measure.js` |")
P(f"| Same with the GPU delegate requested | {g['extraction_ms_per_frame']['median']:.0f} ms ({g['extraction_ms_per_frame']['p95']:.0f}) per frame | `MP_DELEGATE=gpu` |")
P(f"| Decoding and drawing the test frame (not part of the app) | {c['frame_decode_and_draw_ms']['median']:.1f} ms | harness only |")
P(f"| WebSocket round trip with an empty message (reset) | {c['ws_roundtrip_empty_ms']['median']:.1f} ms ({c['ws_roundtrip_empty_ms']['p95']:.1f}) | real `/ws/predict` |")
P(f"| One streamed chunk of 8 frames ({c['stream_chunk_payload_kb']} KB) to the server's reply | {c['ws_stream_chunk_8_frames_ms']['median']:.1f} ms ({c['ws_stream_chunk_8_frames_ms']['p95']:.1f}) | real `/ws/predict`, continuous mode |")
P(f"| Whole sign in one `predict` message ({c['predict_payload_kb']} KB, {min(c['frames_per_sign'])} to {max(c['frames_per_sign'])} frames) to the prediction | {c['ws_predict_whole_sign_ms']['median']:.1f} ms ({c['ws_predict_whole_sign_ms']['p95']:.1f}) | real `/ws/predict`, includes parsing, preprocessing and the model |")
P(f"| Preprocessing one sequence (gap fill, resample to {m['model']['seq_len']} frames) | {m['preprocess_ms']['median']:.2f} ms ({m['preprocess_ms']['p95']:.2f}) | `tools/latency/model_latency.py` |")
P(f"| Model forward pass, one sequence, batch 1, {m['torch_threads']} torch threads | {m['model_forward_ms']['median']:.1f} ms ({m['model_forward_ms']['p95']:.1f}) | {m['validation_sequences']} validation sequences |")
P(f"| MediaPipe start-up (script, model download, first frame) | {c['startup_ms'] / 1000:.1f} s (CPU), {g['startup_ms'] / 1000:.1f} s (GPU requested) | once per page load |")
P(f"| WebSocket connect to the server's ready message | {c['ws_connect_to_ready_ms']:.0f} ms | once per session |\n")
P("## Frame rate\n")
P(f"- Sustained extraction rate with one frame in flight (what the capture loop reaches when the camera is faster): **{c['extraction_fps_sustained']} frames per second** with the CPU delegate, "
  f"{g['extraction_fps_sustained']} with the GPU delegate requested. A 30 fps webcam is therefore sampled at about a quarter of its rate.")
n = sum(c["frames_per_sign"]) / len(c["frames_per_sign"])
P(f"- The training features use every second frame of INCLUDE videos (stride 2). The three test videos have {min(c['frames_per_sign'])} to {max(c['frames_per_sign'])} frames; if a camera delivered such a sign at 30 fps "
  f"(an assumption, the files' frame rate was not read) it would last about {n / 30:.1f} s and give about {n / 30 * c['extraction_fps_sustained']:.0f} extracted frames at this rate, against about {n / 2:.0f} at stride 2. "
  "The recognizer resamples every sign to 32 frames, so a sparse capture is stretched, not rejected. Whether the lower live rate costs accuracy was not measured here.")
P("- The server side is not the bottleneck: the model and the WebSocket together need a few tens of milliseconds per sign, the browser extraction needs about 150 ms per frame.\n")
P("## Limits of this measurement\n")
P("- One machine, headless Chrome, local server, 640x480 input, three sign videos; no camera capture time, no rendering of the page, no network.")
gain = (1 - g["extraction_ms_per_frame"]["median"] / c["extraction_ms_per_frame"]["median"]) * 100
P(f"- The GPU run only requested the GPU delegate; I did not verify that the GPU was actually used. It was {gain:.0f} percent faster per frame here and took longer to start.")
P("- The delay a user sees also includes the time the sign takes and the pause the segmenter waits for before it closes a sign; these are not measured here.")
(EV / "LATENCY.md").write_text("\n".join(o) + "\n", encoding="utf-8", newline="\n")
print("\n".join(o))
