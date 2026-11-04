"use client";
import { cameraBoxStyle, FramingGuide } from "./CameraFrame";
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
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="card-title">Landmark check</h2>
          <button
            onClick={running ? stop : start}
            disabled={state === "starting" || busy}
            className="btn btn-sm"
          >
            {running ? <CameraOff size={16} aria-hidden /> : <Camera size={16} aria-hidden />}
            {state === "starting" ? "Starting…" : running ? "Stop camera" : "Start camera"}
          </button>
        </div>
        <p className="mt-1 text-sm text-ink2">
          Compares the landmarks this browser extracts with the ones Python MediaPipe (used for training) extracts from the same video. A {SECONDS} second
          video of you is recorded locally and offered as a download together with the browser landmarks. Nothing is uploaded; delete the files when
          you are done.
        </p>

        <div className="relative mx-auto mt-3 max-w-3xl overflow-hidden rounded-3xl border border-edge/50 bg-cam text-camfg" style={cameraBoxStyle(capture.resolution)}>
          <video ref={videoRef} playsInline muted className="h-full w-full object-cover" aria-label="Webcam preview" />
          <canvas ref={canvasRef} width={capture.resolution?.width ?? 640} height={capture.resolution?.height ?? 480} className="pointer-events-none absolute inset-0 h-full w-full" />
          <FramingGuide capture={capture} />
          {!running && (
            <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-camfg">
              {state === "starting" ? (extractor === "loading" ? "Loading the landmark model…" : "Waiting for camera…") : "Camera is off."}
            </p>
          )}
          {phase === "countdown" && (
            <p aria-live="assertive" className="absolute inset-0 flex items-center justify-center bg-cam/60 text-8xl font-bold text-camfg">
              {left}
            </p>
          )}
          {phase === "recording" && (
            <p className="absolute left-3 top-3 inline-flex items-center gap-2 rounded-2xl bg-[#b3123a] px-2.5 py-1 text-sm font-extrabold text-white">
              <Circle size={12} fill="currentColor" aria-hidden /> REC {left}s
            </p>
          )}
        </div>
        <CaptureHints capture={capture} />
        {error && (
          <p role="alert" className="mt-3 notice notice-bad">
            {error}
          </p>
        )}
        {problem && (
          <p role="alert" className="mt-2 notice notice-bad">
            {problem}
          </p>
        )}
        <p className="mt-2 text-sm text-ink2">
          Live: {stats.frames} buffered frames, {stats.withPose} with body, {stats.withHands} with hands.
        </p>
        <p className="mt-2 text-sm text-ink2">Keyboard: {shortcutHelp(["record"])}.</p>
        <p className="mt-2 text-sm text-ink2">Sign one sign you know during the recording, with both shoulders and your hands in view.</p>
        <button
          onClick={() => void record()}
          disabled={!running || busy}
          className="mt-3 btn btn-primary"
        >
          {phase === "idle" ? `Record ${SECONDS} s (3-2-1)` : phase === "saving" ? "Saving…" : "Recording…"}
        </button>

        {take && (
          <div aria-live="polite" className="mt-4 space-y-2 notice notice-good">
            <p className="font-semibold">
              Recorded {take.seconds} s: {take.frames} landmark frames from the browser ({take.fps} per second).
            </p>
            <div className="flex flex-wrap gap-2">
              <a className="btn btn-sm" href={take.videoUrl} download={`${take.stem}.${extensionFor(take.mime)}`}>
                <Download size={16} aria-hidden /> Video ({extensionFor(take.mime)})
              </a>
              <a className="btn btn-sm" href={take.landmarksUrl} download={`${take.stem}.landmarks.json`}>
                <Download size={16} aria-hidden /> Browser landmarks (json)
              </a>
            </div>
            <p className="text-sm">Download both, then run this in the backend folder:</p>
            <pre className="overflow-x-auto rounded-xl bg-surface2 p-3 text-sm">{compareCommand(take.stem, take.mime)}</pre>
          </div>
        )}
      </div>
    </section>
  );
}
