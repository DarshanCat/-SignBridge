import type { HolisticResults } from "./landmarks";

export interface HolisticInstance {
  setOptions(o: Record<string, unknown>): void;
  onResults(cb: (r: HolisticResults) => void): void;
  initialize(): Promise<void>;
  send(i: { image: HTMLVideoElement }): Promise<void>;
  close(): Promise<void>;
}

type HolisticCtor = new (c: { locateFile: (f: string) => string }) => HolisticInstance;

const BASE = "/mediapipe/holistic/";
let scriptPromise: Promise<HolisticCtor> | null = null;

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

export async function createHolistic(onResults: (r: HolisticResults) => void): Promise<HolisticInstance> {
  const Holistic = await loadScript();
  const h = new Holistic({ locateFile: (f) => `${BASE}${f}` });
  h.setOptions({
    modelComplexity: 0,
    smoothLandmarks: true,
    refineFaceLandmarks: false,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
  h.onResults(onResults);
  await h.initialize();
  return h;
}
