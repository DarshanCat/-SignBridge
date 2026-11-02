import type { HolisticResults } from "./landmarks";

export interface HolisticInstance {
  setOptions(o: Record<string, unknown>): void;
  onResults(cb: (r: HolisticResults) => void): void;
  initialize(): Promise<void>;
  send(i: { image: HTMLVideoElement | HTMLCanvasElement }): Promise<void>;
  close(): Promise<void>;
}

type HolisticCtor = new (c: { locateFile: (f: string) => string }) => HolisticInstance;

const BASE = "/mediapipe/holistic/";
let scriptPromise: Promise<HolisticCtor> | null = null;

/** What the loader is doing, for the loading indicator. */
export type LoadPhase = "script" | "initialize" | "warmup" | "ready";

export const LOAD_PHASE_TEXT: Record<LoadPhase, string> = {
  script: "Loading MediaPipe script",
  initialize: "Initializing MediaPipe (WebAssembly)",
  warmup: "Preparing the pose and hand models (first frame)",
  ready: "Landmark model ready",
};

/**
 * CPU inference is the default. Measured on the development machine (Intel UHD Graphics, Chrome): the first frame took about 29 s
 * with the default GPU delegate (shader compilation, main thread blocked) and under 1 s with CPU inference, at about 50 ms per frame
 * on an empty image. Set NEXT_PUBLIC_MEDIAPIPE_DELEGATE=gpu to use the GPU delegate instead.
 */
export const USE_CPU_INFERENCE = process.env.NEXT_PUBLIC_MEDIAPIPE_DELEGATE !== "gpu";

/** Load the self-hosted MediaPipe Holistic script once (no CDN). */
function loadScript(): Promise<HolisticCtor> {
  scriptPromise ??= new Promise((resolve, reject) => {
    const get = () => (window as unknown as { Holistic?: HolisticCtor }).Holistic;
    if (get()) return resolve(get()!);
    const s = document.createElement("script");
    s.src = `${BASE}holistic.js`;
    s.crossOrigin = "anonymous";
    s.onload = () => (get() ? resolve(get()!) : reject(new Error("MediaPipe script loaded but Holistic is undefined")));
    s.onerror = () => {
      scriptPromise = null;
      reject(new Error("Could not load MediaPipe files from /mediapipe/holistic (run npm run setup:mediapipe)."));
    };
    document.head.appendChild(s);
  });
  return scriptPromise;
}

/** One gray frame pushed through the graph so the models are built before the camera starts (otherwise the first real frame pays for it). */
async function warmUp(h: HolisticInstance): Promise<void> {
  const c = document.createElement("canvas");
  c.width = 640;
  c.height = 480;
  const ctx = c.getContext("2d");
  if (ctx) {
    ctx.fillStyle = "#808080";
    ctx.fillRect(0, 0, c.width, c.height);
  }
  await h.send({ image: c });
}

export async function createHolistic(
  onResults: (r: HolisticResults) => void,
  onPhase: (p: LoadPhase) => void = () => {},
): Promise<HolisticInstance> {
  onPhase("script");
  const Holistic = await loadScript();
  const h = new Holistic({ locateFile: (f) => `${BASE}${f}` });
  h.setOptions({
    modelComplexity: 0,
    smoothLandmarks: true,
    refineFaceLandmarks: false,
    useCpuInference: USE_CPU_INFERENCE,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
  let live = false; // the warm-up frame must not reach the caller as a landmark result
  h.onResults((r) => {
    if (live) onResults(r);
  });
  onPhase("initialize");
  await h.initialize();
  onPhase("warmup");
  await warmUp(h);
  live = true;
  onPhase("ready");
  return h;
}
