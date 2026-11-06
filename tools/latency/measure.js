// Latency and FPS of the live path, measured in real Chrome with the app's own self-hosted MediaPipe Holistic (same options as lib/holistic.ts, CPU delegate)
// and the real /ws/predict WebSocket of the running API. Frames are real INCLUDE sign video frames (resized to a 640x480 webcam size).
// usage: NODE_PATH=<folder with playwright-core> node tools/latency/measure.js <frames dir> <out.json> [web http://localhost:3110] [api 127.0.0.1:8110]
// The frames dir holds v<k>_<i>.jpg (see make_frames.py in the scratch folder of the run; info.json lists the source videos).
const { chromium } = require("playwright-core");
const fs = require("fs");
const os = require("os");
const path = require("path");
const GPU = process.env.MP_DELEGATE === "gpu"; // MP_DELEGATE=gpu: MediaPipe GPU delegate in a GPU enabled Chrome (the app's default is the CPU delegate)
const [framesDir, outFile, web = "http://localhost:3110", api = "127.0.0.1:8110"] = process.argv.slice(2);
const files = fs.readdirSync(framesDir).filter((f) => /^v\d+_\d+\.jpg$/.test(f)).sort();
const videos = {};
for (const f of files) (videos[f.split("_")[0]] ||= []).push(fs.readFileSync(path.join(framesDir, f)).toString("base64"));

// MediaPipe's packed asset download fails now and then (HTTP 503 in the page, the same intermittent start-up failure that tools/browser_path/run_harness.sh retries),
// so a failed or hung attempt is repeated in a fresh browser, up to 8 times.
async function attempt() {
  const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true, args: GPU ? ["--enable-gpu", "--use-angle=d3d11", "--ignore-gpu-blocklist", "--enable-webgl"] : [] });
  try {
  const page = await (await browser.newContext({ viewport: { width: 800, height: 600 } })).newPage();
  await page.goto(web + "/nonexistent-page", { waitUntil: "load", timeout: 180000 }); // a bare page of the same origin: the app page itself competes with MediaPipe at start-up and makes its loader fail
  const run = page.evaluate(async ({ videos, api, gpu }) => {
    const q = (a, p) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))]; };
    const stat = (a) => ({ n: a.length, median: +q(a, 0.5).toFixed(2), p95: +q(a, 0.95).toFixed(2), min: +Math.min(...a).toFixed(2), max: +Math.max(...a).toFixed(2), mean: +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(2) });
    const out = { chrome: navigator.userAgent, cores: navigator.hardwareConcurrency };
    // 1. start up of MediaPipe Holistic
    let t = performance.now();
    await new Promise((res, rej) => { const s = document.createElement("script"); s.src = "/mediapipe/holistic/holistic.js"; s.onload = res; s.onerror = () => rej(new Error("holistic.js")); document.head.appendChild(s); });
    const h = new window.Holistic({ locateFile: (f) => `/mediapipe/holistic/${f}` });
    h.setOptions({ modelComplexity: 0, smoothLandmarks: true, refineFaceLandmarks: false, useCpuInference: !gpu, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
    let resolveResult = null;
    h.onResults((r) => { if (resolveResult) resolveResult(r); });
    await h.initialize();
    const canvas = document.createElement("canvas"); canvas.width = 640; canvas.height = 480;
    const g = canvas.getContext("2d");
    const sendOne = () => new Promise((res) => { resolveResult = res; h.send({ image: canvas }); });
    g.fillStyle = "#808080"; g.fillRect(0, 0, 640, 480);
    await sendOne();
    out.startup_ms = Math.round(performance.now() - t);
    // 2. extraction time per frame, sequential like the app's loop (one frame in flight), real sign frames, tracking on across a video
    const ys = (16 / 9) / (640 / 480);
    const strip = (pts) => (pts && pts.length ? pts.map((p) => ({ x: p.x, y: p.y * ys, z: p.z ?? 0 })) : null);
    const ext = [], signs = [], decode = [];
    for (const k of Object.keys(videos)) {
      h.reset();
      g.fillStyle = "#808080"; g.fillRect(0, 0, 640, 480); await sendOne();
      const frames = [];
      for (let i = 0; i < videos[k].length; i++) {
        const bin = atob(videos[k][i]); const bytes = new Uint8Array(bin.length); for (let j = 0; j < bin.length; j++) bytes[j] = bin.charCodeAt(j);
        const d0 = performance.now();
        const bmp = await createImageBitmap(new Blob([bytes], { type: "image/jpeg" }));
        g.drawImage(bmp, 0, 0, 640, 480); bmp.close();
        decode.push(performance.now() - d0);
        const t0 = performance.now();
        const r = await sendOne();
        const ms = performance.now() - t0;
        if (i >= 3) ext.push(ms); // the first frames of a video include the detection warm up of the tracker
        const t1 = performance.now();
        frames.push({ pose: strip(r.poseLandmarks), left_hand: strip(r.leftHandLandmarks), right_hand: strip(r.rightHandLandmarks) });
      }
      signs.push(frames);
    }
    out.extraction_ms_per_frame = stat(ext);
    out.extraction_fps_sustained = +(1000 / stat(ext).median).toFixed(1);
    out.frame_decode_and_draw_ms = stat(decode);
    // 3. WebSocket: connect, pure round trip (reset), predict (the whole sign), chunked frames like the app (8 frames per chunk)
    const wsOpen = () => new Promise((res, rej) => { const t0 = performance.now(); const ws = new WebSocket(`ws://${api}/ws/predict`); ws.onerror = () => rej(new Error("ws error")); ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.type === "ready") res({ ws, ms: performance.now() - t0, ready: d }); }; });
    const { ws, ms: connectMs, ready } = await wsOpen();
    out.ws_connect_to_ready_ms = +connectMs.toFixed(1);
    out.model = ready;
    const waitFor = (types) => new Promise((res) => { const prev = ws.onmessage; ws.onmessage = (m) => { const d = JSON.parse(m.data); if (types.includes(d.type)) { ws.onmessage = prev; res(d); } }; });
    const rt = [], pred = [], predPayload = [], chunk = [], chunkPayload = [], serverMs = [];
    for (let i = 0; i < 40; i++) { const t0 = performance.now(); const w = waitFor(["reset_ok"]); ws.send(JSON.stringify({ type: "reset" })); await w; rt.push(performance.now() - t0); }
    out.ws_roundtrip_empty_ms = stat(rt);
    for (let rep = 0; rep < 12; rep++) {
      for (const frames of signs) {
        const msg = JSON.stringify({ type: "predict", frames, commit: true });
        const t0 = performance.now(); const w = waitFor(["prediction", "error"]); ws.send(msg); const d = await w;
        pred.push(performance.now() - t0); predPayload.push(msg.length);
        if (d.type === "error") out.predict_error = d.message;
      }
    }
    out.ws_predict_whole_sign_ms = stat(pred);
    out.predict_payload_kb = +(stat(predPayload).median / 1024).toFixed(1);
    out.frames_per_sign = signs.map((s) => s.length);
    ws.send(JSON.stringify({ type: "reset" }));
    await waitFor(["reset_ok"]);
    for (let rep = 0; rep < 4; rep++) {
      for (const frames of signs) {
        for (let i = 0; i < frames.length; i += 8) {
          const msg = JSON.stringify({ type: "frames", frames: frames.slice(i, i + 8) });
          const t0 = performance.now(); const w = waitFor(["stream", "error", "sign"]); ws.send(msg); await w;
          chunk.push(performance.now() - t0); chunkPayload.push(msg.length);
        }
      }
      ws.send(JSON.stringify({ type: "flush" }));
    }
    out.ws_stream_chunk_8_frames_ms = stat(chunk);
    out.stream_chunk_payload_kb = +(stat(chunkPayload).median / 1024).toFixed(1);
    ws.close();
    return out;
  }, { videos, api, gpu: GPU });
  const result = await Promise.race([run, new Promise((_, rej) => setTimeout(() => rej(new Error("attempt timed out after 240 s")), 240000))]);
  result.machine = { cpu: os.cpus()[0].model, logical_cpus: os.cpus().length, ram_gb: +(os.totalmem() / 1e9).toFixed(1), platform: `${os.platform()} ${os.release()}` };
  result.delegate = GPU ? "gpu (requested)" : "cpu";
  result.note = `Headless Chrome, ${GPU ? "GPU delegate requested" : "CPU delegate (the app's default)"},`+" 640x480 frames from real INCLUDE sign videos, one frame in flight at a time. The server was running locally, so the WebSocket numbers have no network distance.";
  fs.writeFileSync(outFile, JSON.stringify(result, null, 1));
  return result;
  } finally {
    await browser.close().catch(() => {});
  }
}

(async () => {
  for (let i = 1; i <= 8; i++) {
    try {
      const result = await attempt();
      result.attempts = i;
      fs.writeFileSync(outFile, JSON.stringify(result, null, 1));
      console.log(JSON.stringify(result, null, 1));
      return;
    } catch (e) {
      console.error(`attempt ${i} failed: ${String(e.message).split("\n")[0]}`);
    }
  }
  console.error("FAILED after 8 attempts");
  process.exit(1);
})();
