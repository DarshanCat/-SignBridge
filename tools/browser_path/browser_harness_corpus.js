// Frame-stepping harness: real Chrome, the app's own self-hosted MediaPipe Holistic (same options as lib/holistic.ts), the sampled frames of
// one framing fed one by one (so extraction speed never drops frames), landmarks converted like lib/landmarks.ts toFrame (y * (16/9)/aspect).
// usage: node browser_harness.js <16x9|4x3> [firstIndex lastIndex]
const { chromium } = require("playwright-core");
const path = require("path");
const fs = require("fs");
const HERE = process.env.CORPUS_DIR || __dirname;
const [framing, a0, a1] = process.argv.slice(2);
const dims = framing === "16x9" ? { W: 1280, H: 720 } : { W: 640, H: 480 };
const samples = JSON.parse(fs.readFileSync(path.join(HERE, "samples.json"), "utf8")).samples.slice(Number(a0 || 0), a1 ? Number(a1) : undefined);
const outDir = path.join(HERE, "browser", framing);
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
  const page = await (await browser.newContext({ viewport: { width: 800, height: 600 } })).newPage();
  await page.goto("http://localhost:3110/", { waitUntil: "load" });
  await page.evaluate(async () => {
    await new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = "/mediapipe/holistic/holistic.js";
      s.onload = res;
      s.onerror = () => rej(new Error("holistic.js"));
      document.head.appendChild(s);
    });
    const h = new window.Holistic({ locateFile: (f) => `/mediapipe/holistic/${f}` });
    h.setOptions({ modelComplexity: 0, smoothLandmarks: true, refineFaceLandmarks: false, useCpuInference: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
    window.__last = null;
    h.onResults((r) => { window.__last = r; });
    await h.initialize();
    const c = document.createElement("canvas"); c.width = 640; c.height = 480;
    const g = c.getContext("2d"); g.fillStyle = "#808080"; g.fillRect(0, 0, 640, 480);
    await h.send({ image: c });
    window.__h = h;
  });
  const t00 = Date.now();
  for (const s of samples) {
    const file = path.join(outDir, `${s.id}.json`);
    if (fs.existsSync(file)) continue;
    const t0 = Date.now();
    const frames = await page.evaluate(async ({ id, framing, W, H, port }) => {
      const h = window.__h;
      h.reset();
      const gray = document.createElement("canvas"); gray.width = 640; gray.height = 480;
      const gg = gray.getContext("2d"); gg.fillStyle = "#808080"; gg.fillRect(0, 0, 640, 480);
      await h.send({ image: gray }); // flush tracking state between videos
      const c = document.createElement("canvas"); c.width = W; c.height = H;
      const g = c.getContext("2d");
      const ys = (16 / 9) / (W / H);
      const strip = (pts) => (pts && pts.length ? pts.map((p) => ({ x: p.x, y: p.y * ys, z: p.z ?? 0 })) : null);
      const out = [];
      for (let i = 0; ; i++) {
        const resp = await fetch(`http://127.0.0.1:${port}/${framing}/${id}/${String(i).padStart(3, "0")}.jpg`);
        if (!resp.ok) break;
        const bmp = await createImageBitmap(await resp.blob());
        g.drawImage(bmp, 0, 0, W, H);
        bmp.close();
        window.__last = null;
        await h.send({ image: c });
        const r = window.__last || {};
        out.push({ pose: strip(r.poseLandmarks), left_hand: strip(r.leftHandLandmarks), right_hand: strip(r.rightHandLandmarks) });
      }
      return out;
    }, { id: s.id, framing, W: dims.W, H: dims.H, port: Number(process.env.FRAMES_PORT) });
    fs.writeFileSync(file, JSON.stringify({ id: s.id, aspect: dims.W / dims.H, frames }));
    const withPose = frames.filter((f) => f.pose).length;
    console.log(s.id, s.label, `${frames.length} frames, pose in ${withPose}, ${((Date.now() - t0) / 1000).toFixed(1)} s (elapsed ${((Date.now() - t00) / 60000).toFixed(1)} min)`);
  }
  await browser.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 500)); process.exit(1); });
