"use client";
import { Camera, CameraOff, ScanSearch, ShieldCheck } from "lucide-react";
import { useRef, useState } from "react";
import { apiPost, type LandmarkSequenceResult, type SignTranslation } from "@/lib/api";
import type { LandmarkCapture } from "./useLandmarkCapture";

type Check =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "done"; result: LandmarkSequenceResult }
  | { kind: "error"; message: string };

type Recognition =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "done"; result: SignTranslation; ms: number }
  | { kind: "error"; message: string };

export function WebcamPanel({
  capture,
  backendUp,
  modelLoaded,
}: {
  capture: LandmarkCapture;
  backendUp: boolean;
  modelLoaded: boolean;
}) {
  const { state, extractor, error, stats, runId, videoRef, canvasRef, start, stop, getBuffer } = capture;
  // Results are tagged with the camera run that produced them and only shown for the current run, so stopping the
  // camera (or restarting it) discards old and late results without any state reset.
  const [checkState, setCheckState] = useState<{ runId: number; value: Check }>({ runId: -1, value: { kind: "idle" } });
  const [recState, setRecState] = useState<{ runId: number; value: Recognition }>({ runId: -1, value: { kind: "idle" } });
  const running = state === "running";
  const idle = { kind: "idle" } as const;
  const check: Check = running && checkState.runId === runId ? checkState.value : idle;
  const rec: Recognition = running && recState.runId === runId ? recState.value : idle;
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

  async function recognize() {
    if (inFlight.current) return;
    inFlight.current = true;
    const mine = runId;
    setRecState({ runId: mine, value: { kind: "busy" } });
    const t0 = performance.now();
    try {
      const result = await apiPost<SignTranslation>("/api/signs/translate", { frames: getBuffer() });
      setRecState({ runId: mine, value: { kind: "done", result, ms: Math.round(performance.now() - t0) } });
    } catch (e) {
      setRecState({ runId: mine, value: { kind: "error", message: e instanceof Error ? e.message : "Recognition failed." } });
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

      <div className="relative mt-3 aspect-[4/3] overflow-hidden rounded-lg bg-black/60">
        <video ref={videoRef} playsInline muted className="h-full w-full object-cover" aria-label="Webcam preview" />
        <canvas ref={canvasRef} width={640} height={480} className="pointer-events-none absolute inset-0 h-full w-full" />
        {!running && (
          <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-slate-400">
            {busy
              ? extractor === "loading"
                ? "Loading MediaPipe landmark extraction…"
                : "Waiting for camera…"
              : "Camera is off. Video stays in your browser and is never recorded or uploaded."}
          </p>
        )}
      </div>

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
          disabled={!running || !backendUp || stats.frames === 0 || check.kind === "busy" || rec.kind === "busy"}
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

      <div className="mt-4 rounded-lg border border-white/10 p-3">
        <button
          onClick={recognize}
          disabled={!running || !backendUp || !modelLoaded || stats.frames === 0 || rec.kind === "busy" || check.kind === "busy"}
          className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-ink disabled:opacity-40"
        >
          <ScanSearch size={16} aria-hidden /> Recognize sign
        </button>
        {!modelLoaded && (
          <p className="mt-2 text-xs text-amber-300">
            Recognition is unavailable: no trained sign-recognition model is loaded, so no signs, glosses, confidence
            scores or English output are produced.
          </p>
        )}
        <p className="mt-2 text-xs text-slate-400">
          Recognizes one isolated sign from the last ~2 seconds of landmarks. Continuous signing is not segmented.
        </p>
        <div aria-live="polite" className="mt-2 space-y-1 text-sm">
          {rec.kind === "error" && <p className="text-rose-300">{rec.message}</p>}
          {rec.kind === "done" && (
            <>
              <ul className="text-xs text-slate-300">
                {rec.result.predictions.map((p) => (
                  <li key={p.label}>
                    {p.label}: {(p.confidence * 100).toFixed(1)}%
                  </li>
                ))}
              </ul>
              <p className={rec.result.accepted ? "text-emerald-300" : "text-amber-300"}>{rec.result.message}</p>
              {rec.result.accepted && rec.result.gloss.length > 0 && <p>Gloss: {rec.result.gloss.join(" ")}</p>}
              {rec.result.english && <p className="text-base font-medium">{rec.result.english}</p>}
              <p className="text-xs text-slate-500">Measured round trip: {rec.ms} ms (browser to API and back).</p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
