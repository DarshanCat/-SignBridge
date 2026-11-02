"use client";
import { Camera, CameraOff, Circle } from "lucide-react";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { apiPost, type RecordResult } from "@/lib/api";
import { parseClip, type SignClip } from "@/lib/avatar/clip";
import { SequencePlayer } from "@/lib/avatar/player";
import { buildRecordRequest, countdownSteps, DURATIONS_S, isValidGloss, normalizeGloss } from "@/lib/recorder";
import { shortcutHelp } from "@/lib/shortcuts";
import { CaptureHints } from "./CaptureHints";
import { RecordSessionPanel } from "./RecordSessionPanel";
import { useShortcuts } from "./useShortcuts";
import type { LandmarkCapture } from "./useLandmarkCapture";

const AvatarViewer = dynamic(() => import("./avatar/AvatarViewer"), {
  ssr: false,
  loading: () => <p className="flex h-full items-center justify-center text-sm text-slate-400">Loading 3D scene…</p>,
});

type Phase = { kind: "idle" } | { kind: "countdown"; n: number } | { kind: "recording"; left: number } | { kind: "sending" };

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Record a sign for the vocabulary: webcam with landmark overlay, countdown, fixed duration, landmarks only (no video) sent to the API. */
export function RecordSignPanel({ capture, backendUp }: { capture: LandmarkCapture; backendUp: boolean }) {
  const { state, extractor, error, stats, videoRef, canvasRef, start, stop, beginRecording, endRecording } = capture;
  const [mode, setMode] = useState<"single" | "session">("single");
  const [gloss, setGloss] = useState("");
  const [seconds, setSeconds] = useState<number>(3);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [result, setResult] = useState<RecordResult | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [player] = useState(() => new SequencePlayer());
  const cancelled = useRef(false);
  const running = state === "running";
  const busy = phase.kind !== "idle";
  const canRecord = running && backendUp && !busy && isValidGloss(gloss);

  useEffect(
    () => () => {
      cancelled.current = true;
      player.dispose();
    },
    [player],
  );

  async function record() {
    setResult(null);
    setProblem(null);
    player.load([]);
    cancelled.current = false;
    for (const n of countdownSteps()) {
      setPhase({ kind: "countdown", n });
      await sleep(1000);
      if (cancelled.current) return;
    }
    beginRecording();
    const t0 = performance.now();
    const total = seconds * 1000;
    while (performance.now() - t0 < total) {
      setPhase({ kind: "recording", left: Math.ceil((total - (performance.now() - t0)) / 1000) });
      await sleep(100);
      if (cancelled.current) {
        endRecording();
        return;
      }
    }
    const frames = endRecording();
    const elapsed = performance.now() - t0;
    setPhase({ kind: "sending" });
    try {
      const res = await apiPost<RecordResult>("/api/record/sign", buildRecordRequest(gloss, frames, elapsed));
      setResult(res);
      if (res.accepted && res.clip) {
        player.load([parseClip(res.clip)] as SignClip[]);
        player.play();
      }
    } catch (e) {
      setProblem(e instanceof Error ? e.message : "Saving the take failed.");
    } finally {
      setPhase({ kind: "idle" });
    }
  }

  useShortcuts({
    record: mode === "single" && canRecord ? () => void record() : undefined,
    replay: mode === "single" && result?.accepted ? () => player.restart() : undefined,
  });

  const toggle = (
    <div role="group" aria-label="Recording mode" className="flex gap-2">
      {(["single", "session"] as const).map((m) => (
        <button
          key={m}
          onClick={() => setMode(m)}
          disabled={busy}
          aria-pressed={mode === m}
          className={`min-h-11 rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 ${mode === m ? "bg-accent text-ink" : "bg-white/10 text-slate-200"}`}
        >
          {m === "single" ? "Single sign" : "Guided session"}
        </button>
      ))}
    </div>
  );

  if (mode === "session") {
    return (
      <div className="space-y-4">
        {toggle}
        <RecordSessionPanel capture={capture} backendUp={backendUp} />
      </div>
    );
  }

  return (
    <section className="space-y-4" aria-label="Record sign">
      {toggle}
      <div className="rounded-xl border border-white/10 bg-panel p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Record a sign</h2>
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
          For signs the INCLUDE dataset lacks. Only landmarks are sent and stored (no video), in the same 225 feature format as INCLUDE. A take is rejected if
          too many frames have no hand or no body.
        </p>

        <div className="relative mt-3 aspect-[4/3] overflow-hidden rounded-lg bg-black/60">
          <video ref={videoRef} playsInline muted className="h-full w-full object-cover" aria-label="Webcam preview" />
          <canvas ref={canvasRef} width={640} height={480} className="pointer-events-none absolute inset-0 h-full w-full" />
          {!running && (
            <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-slate-400">
              {state === "starting" ? (extractor === "loading" ? "Loading the landmark model…" : "Waiting for camera…") : "Camera is off."}
            </p>
          )}
          {phase.kind === "countdown" && (
            <p aria-live="assertive" className="absolute inset-0 flex items-center justify-center bg-black/40 text-8xl font-bold">
              {phase.n}
            </p>
          )}
          {phase.kind === "recording" && (
            <p className="absolute left-3 top-3 inline-flex items-center gap-2 rounded bg-rose-600 px-2 py-1 text-sm font-semibold">
              <Circle size={12} fill="currentColor" aria-hidden /> REC {phase.left}s
            </p>
          )}
        </div>
        <CaptureHints capture={capture} />
        {error && (
          <p role="alert" className="mt-3 rounded-lg bg-rose-500/15 p-3 text-sm text-rose-200">
            {error}
          </p>
        )}
        <p className="mt-2 text-xs text-slate-400">
          Live: {stats.frames} buffered frames, {stats.withPose} with body, {stats.withHands} with hands.
        </p>

        <form
          className="mt-3 flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            void record();
          }}
        >
          <label className="text-xs text-slate-300">
            Gloss name
            <input
              value={gloss}
              onChange={(e) => setGloss(e.target.value)}
              maxLength={40}
              placeholder="e.g. WATER"
              className="mt-1 block w-48 rounded-lg border border-white/10 bg-ink px-3 py-2 text-sm"
            />
          </label>
          <label className="text-xs text-slate-300">
            Duration
            <select value={seconds} onChange={(e) => setSeconds(Number(e.target.value))} className="mt-1 block rounded-lg bg-ink px-3 py-2 text-sm">
              {DURATIONS_S.map((d) => (
                <option key={d} value={d}>
                  {d} s
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={!canRecord}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
          >
            {busy ? (phase.kind === "sending" ? "Saving…" : "Recording…") : "Record (3-2-1)"}
          </button>
        </form>
        {gloss.trim() !== "" && !isValidGloss(gloss) && <p className="mt-2 text-xs text-amber-300">Use letters, digits and hyphens only (up to 32 characters).</p>}
        {gloss.trim() !== "" && isValidGloss(gloss) && <p className="mt-2 text-xs text-slate-400">Will be saved as {normalizeGloss(gloss)}.</p>}
        {!backendUp && <p role="alert" className="mt-2 text-xs text-amber-300">Backend unreachable: recordings cannot be saved. Start it with scripts\serve.ps1.</p>}
        <p className="mt-2 text-xs text-slate-500">Keyboard (when not typing in a field): {shortcutHelp(["record", "replay"])}.</p>
        {problem && (
          <p role="alert" className="mt-2 rounded-lg bg-rose-500/15 p-2 text-sm text-rose-200">
            {problem}
          </p>
        )}

        <div aria-live="polite" className="mt-3 space-y-1 text-sm">
          {result && !result.accepted && (
            <div className="rounded-lg bg-amber-400/10 p-3 text-amber-200">
              <p className="font-semibold">Take rejected and not saved.</p>
              <ul className="mt-1 list-disc pl-5 text-xs">
                {result.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          )}
          {result && result.accepted && (
            <div className="rounded-lg bg-emerald-400/10 p-3 text-emerald-200">
              <p className="font-semibold">Saved {result.gloss}.</p>
              <p className="mt-1 text-xs">
                {result.stats.frames} frames in {result.stats.seconds}s ({result.stats.fps} fps), {result.stats.no_hand_frames} without a hand. Features:
                data/recorded/{result.feature_file}. Clip: data/recorded/{result.clip_file} (self-recorded, not signer reviewed; copy it into
                frontend/public/animations and register it to use it).
              </p>
            </div>
          )}
        </div>
      </div>

      {result?.accepted && (
        <div className="rounded-xl border border-white/10 bg-panel p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Preview of the retargeted take</h3>
          <div className="mt-2 aspect-[4/3] overflow-hidden rounded-lg bg-black/60">
            <AvatarViewer player={player} onKind={() => {}} />
          </div>
          <div className="mt-2 flex gap-2">
            <button className="rounded-lg bg-white/10 px-3 py-2 text-sm" onClick={() => player.restart()}>
              Replay
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
