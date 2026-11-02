"use client";
import { Camera, CameraOff, Circle, Download } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { USE_CPU_INFERENCE } from "@/lib/holistic";
import type { LandmarkFrame } from "@/lib/landmarks";
import { buildCheckFile, compareCommand, extensionFor, fileStem, pickMimeType } from "@/lib/landmarkCheck";
import { countdownSteps } from "@/lib/recorder";
import { shortcutHelp } from "@/lib/shortcuts";
import { CaptureHints } from "./CaptureHints";
import { useShortcuts } from "./useShortcuts";
import type { LandmarkCapture } from "./useLandmarkCapture";

const SECONDS = 4;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

interface Take {
  stem: string;
  mime: string;
  videoUrl: string;
  landmarksUrl: string;
  frames: number;
  seconds: number;
  fps: number;
}

/**
 * Landmark check: records a short video of the camera and, at the same time, the landmarks the browser extracts from it. Both stay in
 * this browser; nothing is sent anywhere. The two files are offered as downloads so `training.compare_landmarks` can run Python MediaPipe
 * on the same video and report how far the landmark sets differ.
 */
export function LandmarkCheckPanel({ capture }: { capture: LandmarkCapture }) {
  const { state, extractor, error, stats, videoRef, canvasRef, start, stop, getStream, setFrameListener } = capture;
  const [phase, setPhase] = useState<"idle" | "countdown" | "recording" | "saving">("idle");
  const [left, setLeft] = useState(0);
  const [take, setTake] = useState<Take | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const urls = useRef<string[]>([]);
  const running = state === "running";
  const busy = phase !== "idle";
  const canRecord = running && !busy;

  const revoke = () => {
    urls.current.forEach((u) => URL.revokeObjectURL(u));
    urls.current = [];
  };
  useEffect(
    () => () => {
      setFrameListener(null);
      revoke();
    },
    [setFrameListener],
  );

  async function record() {
    const stream = getStream();
    setProblem(null);
    setTake(null);
    revoke();
    if (!stream) return setProblem("Start the camera first.");
    if (typeof MediaRecorder === "undefined") return setProblem("This browser cannot record video (MediaRecorder is missing).");
    const mime = pickMimeType((m) => MediaRecorder.isTypeSupported(m));
    if (!mime) return setProblem("This browser supports none of the video formats the check can use (WebM or MP4).");

    for (const n of countdownSteps()) {
      setPhase("countdown");
      setLeft(n);
      await sleep(1000);
    }
    const frames: LandmarkFrame[] = [];
    const times: number[] = [];
    const chunks: BlobPart[] = [];
    const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 2_500_000 });
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    const started = new Promise<number>((res) => (rec.onstart = () => res(performance.now())));
    const stopped = new Promise<number>((res) => (rec.onstop = () => res(performance.now())));
    setFrameListener((f, t) => {
      frames.push(f);
      times.push(t);
    });
    rec.start();
    const t0 = await started;
    setPhase("recording");
    for (let s = SECONDS; s > 0; s--) {
      setLeft(s);
      await sleep(1000);
    }
    rec.stop();
    const t1 = await stopped;
    setFrameListener(null);
    setPhase("saving");
    const stem = fileStem(new Date());
    const durationMs = t1 - t0;
    const file = buildCheckFile(stem, mime, durationMs, frames, times, t0, USE_CPU_INFERENCE, new Date(),
      videoRef.current?.videoWidth && videoRef.current?.videoHeight ? videoRef.current.videoWidth / videoRef.current.videoHeight : null);
    const videoUrl = URL.createObjectURL(new Blob(chunks, { type: mime }));
    const landmarksUrl = URL.createObjectURL(new Blob([JSON.stringify(file)], { type: "application/json" }));
    urls.current = [videoUrl, landmarksUrl];
    setTake({ stem, mime, videoUrl, landmarksUrl, frames: file.frames.length, seconds: Math.round(durationMs / 100) / 10, fps: Math.round((file.frames.length / (durationMs / 1000)) * 10) / 10 });
    setPhase("idle");
  }

  useShortcuts({ record: canRecord ? () => void record() : undefined });

  return (
    <section className="space-y-4" aria-label="Landmark check">
      <div className="rounded-xl border border-white/10 bg-panel p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Landmark check</h2>
          <button
            onClick={running ? stop : start}
            disabled={state === "starting" || busy}
            className="inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm disabled:opacity-50"
          >
            {running ? <CameraOff size={16} aria-hidden /> : <Camera size={16} aria-hidden />}
            {state === "starting" ? "Starting…" : running ? "Stop camera" : "Start camera"}
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Compares the landmarks this browser extracts with the ones Python MediaPipe (used for training) extracts from the same video. A {SECONDS} second
          video of you is recorded locally and offered as a download together with the browser landmarks. Nothing is uploaded; delete the files when
          you are done.
        </p>

        <div className="relative mt-3 aspect-[4/3] overflow-hidden rounded-lg bg-black/60">
          <video ref={videoRef} playsInline muted className="h-full w-full object-cover" aria-label="Webcam preview" />
          <canvas ref={canvasRef} width={640} height={480} className="pointer-events-none absolute inset-0 h-full w-full" />
          {!running && (
            <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-slate-400">
              {state === "starting" ? (extractor === "loading" ? "Loading the landmark model…" : "Waiting for camera…") : "Camera is off."}
            </p>
          )}
          {phase === "countdown" && (
            <p aria-live="assertive" className="absolute inset-0 flex items-center justify-center bg-black/40 text-8xl font-bold">
              {left}
            </p>
          )}
          {phase === "recording" && (
            <p className="absolute left-3 top-3 inline-flex items-center gap-2 rounded bg-rose-600 px-2 py-1 text-sm font-semibold">
              <Circle size={12} fill="currentColor" aria-hidden /> REC {left}s
            </p>
          )}
        </div>
        <CaptureHints capture={capture} />
        {error && (
          <p role="alert" className="mt-3 rounded-lg bg-rose-500/15 p-3 text-sm text-rose-200">
            {error}
          </p>
        )}
        {problem && (
          <p role="alert" className="mt-2 rounded-lg bg-rose-500/15 p-2 text-sm text-rose-200">
            {problem}
          </p>
        )}
        <p className="mt-2 text-xs text-slate-400">
          Live: {stats.frames} buffered frames, {stats.withPose} with body, {stats.withHands} with hands.
        </p>
        <p className="mt-2 text-xs text-slate-500">Keyboard: {shortcutHelp(["record"])}.</p>
        <p className="mt-2 text-xs text-slate-400">Sign one sign you know during the recording, with both shoulders and your hands in view.</p>
        <button
          onClick={() => void record()}
          disabled={!running || busy}
          className="mt-3 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
        >
          {phase === "idle" ? `Record ${SECONDS} s (3-2-1)` : phase === "saving" ? "Saving…" : "Recording…"}
        </button>

        {take && (
          <div aria-live="polite" className="mt-4 space-y-2 rounded-lg bg-emerald-400/10 p-3 text-sm text-emerald-100">
            <p className="font-semibold">
              Recorded {take.seconds} s: {take.frames} landmark frames from the browser ({take.fps} per second).
            </p>
            <div className="flex flex-wrap gap-2">
              <a className="inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2" href={take.videoUrl} download={`${take.stem}.${extensionFor(take.mime)}`}>
                <Download size={16} aria-hidden /> Video ({extensionFor(take.mime)})
              </a>
              <a className="inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2" href={take.landmarksUrl} download={`${take.stem}.landmarks.json`}>
                <Download size={16} aria-hidden /> Browser landmarks (json)
              </a>
            </div>
            <p className="text-xs">Download both, then run this in the backend folder:</p>
            <pre className="overflow-x-auto rounded bg-black/40 p-2 text-xs">{compareCommand(take.stem, take.mime)}</pre>
          </div>
        )}
      </div>
    </section>
  );
}
