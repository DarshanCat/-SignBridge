"use client";
import { cameraBoxStyle, FramingGuide } from "./CameraFrame";
import { Camera, CameraOff, ScanSearch, ShieldCheck } from "lucide-react";
import { useRef, useState } from "react";
import { apiPost, type LandmarkSequenceResult } from "@/lib/api";
import { CaptureHints } from "./CaptureHints";
import { PredictionPanel } from "./PredictionPanel";
import type { LandmarkCapture } from "./useLandmarkCapture";

type Check =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "done"; result: LandmarkSequenceResult }
  | { kind: "error"; message: string };

export function WebcamPanel({
  capture,
  backendUp,
}: {
  capture: LandmarkCapture;
  backendUp: boolean;
}) {
  const { state, extractor, error, stats, runId, videoRef, canvasRef, start, stop, getBuffer } = capture;
  // Results are tagged with the camera run that produced them and only shown for the current run, so stopping the
  // camera (or restarting it) discards old and late results without any state reset.
  const [checkState, setCheckState] = useState<{ runId: number; value: Check }>({ runId: -1, value: { kind: "idle" } });
  const running = state === "running";
  const idle = { kind: "idle" } as const;
  const check: Check = running && checkState.runId === runId ? checkState.value : idle;
  const inFlight = useRef(false); // at most one server request at a time (no duplicate inference)
  const busy = state === "starting";

  async function validate() {
    if (inFlight.current) return;
    inFlight.current = true;
    const mine = runId;
    setCheckState({ runId: mine, value: { kind: "busy" } });
    try {
      const result = await apiPost<LandmarkSequenceResult>("/api/landmarks/extract", { frames: getBuffer() });
      setCheckState({ runId: mine, value: { kind: "done", result } });
    } catch (e) {
      setCheckState({ runId: mine, value: { kind: "error", message: e instanceof Error ? e.message : "Validation failed." } });
    } finally {
      inFlight.current = false;
    }
  }

  return (
    <section className="rounded-xl border border-white/10 bg-panel p-4" aria-label="Webcam and landmarks">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">ISL Sign to English</h2>
        <button
          onClick={running ? stop : start}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-ink disabled:opacity-60"
        >
          {running ? <CameraOff size={16} aria-hidden /> : <Camera size={16} aria-hidden />}
          {busy ? "Starting…" : running ? "Stop camera" : "Start camera"}
        </button>
      </div>

      <div className="relative mt-3 overflow-hidden rounded-lg bg-black/60" style={cameraBoxStyle(capture.resolution)}>
        <video ref={videoRef} playsInline muted className="h-full w-full object-cover" aria-label="Webcam preview" />
        <canvas ref={canvasRef} width={capture.resolution?.width ?? 640} height={capture.resolution?.height ?? 480} className="pointer-events-none absolute inset-0 h-full w-full" />
        <FramingGuide capture={capture} />
        {!running && (
          <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-slate-400">
            {busy
              ? extractor === "loading"
                ? "Loading the landmark model…"
                : "Waiting for camera…"
              : "Camera is off. Video stays in your browser and is never recorded or uploaded."}
          </p>
        )}
      </div>

      <CaptureHints capture={capture} />

      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-rose-500/15 p-3 text-sm text-rose-200">
          {error}
        </p>
      )}

      <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        {[
          ["Buffered frames", stats.frames],
          ["With body pose", stats.withPose],
          ["With hands", stats.withHands],
        ].map(([k, v]) => (
          <div key={k} className="rounded-lg bg-white/5 p-2">
            <dd className="text-lg font-semibold">{v}</dd>
            <dt className="text-slate-400">{k}</dt>
          </div>
        ))}
      </dl>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          onClick={validate}
          disabled={!running || !backendUp || stats.frames === 0 || check.kind === "busy"}
          className="inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm disabled:opacity-50"
        >
          <ShieldCheck size={16} aria-hidden /> Validate landmarks on server
        </button>
        {!backendUp && <span className="text-xs text-amber-300">Backend unreachable.</span>}
      </div>

      <div aria-live="polite" className="mt-2 text-sm">
        {check.kind === "done" && (
          <p className={check.result.usable ? "text-emerald-300" : "text-amber-300"}>
            {check.result.usable
              ? `Sequence usable: ${check.result.valid_frames}/${check.result.num_frames} valid frames, ${check.result.frames_with_hands} with hands (${check.result.feature_dim} features/frame).`
              : check.result.warnings.join(" ")}
          </p>
        )}
        {check.kind === "error" && <p className="text-rose-300">{check.message}</p>}
      </div>

      <PredictionPanel running={running} runId={runId} bufferFrames={stats.frames} getBuffer={getBuffer} setFrameListener={capture.setFrameListener} />

    </section>
  );
}
