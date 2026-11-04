"use client";
import { cameraBoxStyle, FramingGuide } from "./CameraFrame";
import { Camera, CameraOff, Circle, SkipForward, SquareStop, StepBack } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { apiGet, type RecordPlan, type RecordResult, type RecordTakes } from "@/lib/api";
import { DURATIONS_S } from "@/lib/recorder";
import {
  applyTake,
  currentGloss,
  DEFAULT_TAKES,
  MAX_TAKES,
  MIN_TAKES,
  normalizeSigner,
  parseGlossList,
  previousGloss,
  progress,
  skipGloss,
  startSession,
  validateConfig,
  type SessionState,
} from "@/lib/recordSession";
import { shortcutHelp } from "@/lib/shortcuts";
import { CaptureHints } from "./CaptureHints";
import type { LandmarkCapture } from "./useLandmarkCapture";
import { useShortcuts } from "./useShortcuts";
import { useTakeRecorder } from "./useTakeRecorder";

const btn = "btn btn-sm";

/**
 * Guided recording session: one gloss at a time, N saved takes each, for one signer. Takes go to data/recorded/<signer>/<GLOSS>/ as landmarks
 * only (no video). Rejected takes are explained and do not count; stopping and starting again with the same signer ID resumes where it ended.
 */
export function RecordSessionPanel({ capture, backendUp }: { capture: LandmarkCapture; backendUp: boolean }) {
  const { state, extractor, error, stats, videoRef, canvasRef, start, stop } = capture;
  const running = state === "running";
  const recorder = useTakeRecorder(capture);
  const [signerId, setSignerId] = useState("");
  const [takes, setTakes] = useState(DEFAULT_TAKES);
  const [glossText, setGlossText] = useState("");
  const [plan, setPlan] = useState<RecordPlan | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [presetNote, setPresetNote] = useState<string | null>(null);
  const [seconds, setSeconds] = useState<number>(3);
  const [session, setSession] = useState<SessionState | null>(null);
  const [last, setLast] = useState<{ gloss: string; result: RecordResult | null; error: string | null } | null>(null);
  const [setupErrors, setSetupErrors] = useState<string[]>([]);
  const filled = useRef(false);

  useEffect(() => {
    if (!backendUp) return;
    const ctl = new AbortController();
    apiGet<RecordPlan>("/api/record/plan", ctl.signal)
      .then((p) => {
        setPlan(p);
        setPlanError(null);
        if (!filled.current) {
          filled.current = true;
          setGlossText(p.glosses.join("\n"));
        }
      })
      .catch((e) => {
        if (!ctl.signal.aborted) setPlanError(e instanceof Error ? e.message : "Could not load the list of signs to record.");
      });
    return () => ctl.abort();
  }, [backendUp]);

  /** Fill the sign list from a preset: undefined is the 50 grammar words, "conversation" only the conversation vocabulary signs that must be recorded. */
  async function loadPreset(preset: "conversation" | undefined) {
    try {
      const p = await apiGet<RecordPlan>(preset ? `/api/record/plan?preset=${preset}` : "/api/record/plan");
      setGlossText(p.glosses.join("\n"));
      setPlanError(null);
      setPresetNote(preset ? `${p.glosses.length} signs to record (the others of the vocabulary are INCLUDE classes the model already knows)` : `${p.glosses.length} grammar words`);
    } catch (e) {
      setPlanError(e instanceof Error ? e.message : "Could not load the preset.");
    }
  }

  const gloss = session ? currentGloss(session) : null;
  const canRecord = running && backendUp && !!session && !!gloss && !recorder.busy;

  async function startSessionClicked() {
    const { glosses, invalid } = parseGlossList(glossText);
    const cfg = { signerId, glosses, takesPerGloss: takes };
    const errs = validateConfig(cfg);
    if (invalid.length) errs.push(`Not valid sign names: ${invalid.join(", ")}.`);
    setSetupErrors(errs);
    if (errs.length) return;
    let existing: Record<string, number> = {};
    try {
      existing = (await apiGet<RecordTakes>(`/api/record/takes?signer_id=${encodeURIComponent(normalizeSigner(signerId))}`)).counts;
    } catch {
      setSetupErrors(["Could not read the takes already saved for this signer (is the backend running?). Nothing was started."]);
      return;
    }
    setLast(null);
    setSession(startSession(cfg, existing));
  }

  async function record() {
    if (!session || !gloss) return;
    const out = await recorder.recordTake(gloss, seconds, { signerId: session.config.signerId, makeClip: false });
    if (!out) return;
    setLast({ gloss, result: out.result, error: out.error });
    if (out.result) setSession((s) => (s ? applyTake(s, out.result!.accepted) : s));
  }

  useShortcuts({ record: canRecord ? () => void record() : undefined });

  const p = session ? progress(session) : null;
  const pct = p && p.targetTakes ? Math.round((p.takes / p.targetTakes) * 100) : 0;

  return (
    <section className="space-y-4" aria-label="Guided recording session">
      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="card-title">Guided session</h2>
          <button onClick={running ? stop : start} disabled={state === "starting" || recorder.busy} className={btn}>
            {running ? <CameraOff size={16} aria-hidden /> : <Camera size={16} aria-hidden />}
            {state === "starting" ? "Starting…" : running ? "Stop camera" : "Start camera"}
          </button>
        </div>
        <p className="mt-1 text-sm text-ink2">
          Records several takes of each sign for one signer. Only landmarks are stored (no video), under data/recorded/&lt;signer ID&gt;/&lt;SIGN&gt;/. Get the
          consent of the person you record and use an ID, not a name.
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
          {recorder.phase.kind === "countdown" && (
            <p aria-live="assertive" className="absolute inset-0 flex items-center justify-center bg-cam/60 text-8xl font-bold text-camfg">
              {recorder.phase.n}
            </p>
          )}
          {recorder.phase.kind === "recording" && (
            <p className="absolute left-3 top-3 inline-flex items-center gap-2 rounded-2xl bg-[#b3123a] px-2.5 py-1 text-sm font-extrabold text-white">
              <Circle size={12} fill="currentColor" aria-hidden /> REC {recorder.phase.left}s
            </p>
          )}
        </div>
        <CaptureHints capture={capture} />
        {error && (
          <p role="alert" className="mt-3 notice notice-bad">
            {error}
          </p>
        )}
        <p className="mt-2 text-sm text-ink2">
          Live: {stats.frames} buffered frames, {stats.withPose} with body, {stats.withHands} with hands.
        </p>

        {!session && (
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap gap-3">
              <label className="text-sm text-ink2">
                Signer ID
                <input
                  value={signerId}
                  onChange={(e) => setSignerId(e.target.value)}
                  maxLength={32}
                  placeholder="e.g. P01"
                  className="input mt-1 block !w-32 !text-base"
                />
              </label>
              <label className="text-sm text-ink2">
                Takes per sign
                <input
                  type="number"
                  min={MIN_TAKES}
                  max={MAX_TAKES}
                  value={takes}
                  onChange={(e) => setTakes(Number(e.target.value))}
                  className="input mt-1 block !w-24 !text-base"
                />
              </label>
              <label className="text-sm text-ink2">
                Seconds per take
                <select value={seconds} onChange={(e) => setSeconds(Number(e.target.value))} className="input mt-1 block !w-auto !text-base">
                  {DURATIONS_S.map((d) => (
                    <option key={d} value={d}>
                      {d} s
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Sign list presets">
              <span className="text-sm text-ink2">Preset:</span>
              <button type="button" className="btn btn-sm" disabled={!backendUp} onClick={() => void loadPreset(undefined)}>
                50 grammar words
              </button>
              <button type="button" className="btn btn-sm" disabled={!backendUp} onClick={() => void loadPreset("conversation")}>
                Conversation vocabulary
              </button>
              {presetNote && <span className="text-sm text-ink2" aria-live="polite">{presetNote}</span>}
            </div>
            <label className="block text-sm text-ink2">
              Signs to record, in order (a preset above fills this list; edit freely)
              <textarea
                value={glossText}
                onChange={(e) => setGlossText(e.target.value)}
                rows={6}
                className="input mt-1 block !font-mono !text-base"
                spellCheck={false}
              />
            </label>
            {planError && <p className="text-sm text-warnfg">{planError}</p>}
            {!backendUp && <p role="alert" className="text-sm text-warnfg">Backend unreachable: takes cannot be saved. Start it with scripts\serve.ps1.</p>}
            {setupErrors.length > 0 && (
              <ul role="alert" className="notice notice-bad">
                {setupErrors.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            )}
            <button onClick={() => void startSessionClicked()} disabled={!backendUp} className="btn btn-primary">
              Start session
            </button>
            <p className="text-sm text-ink2">Starting again with the same signer ID continues where that signer stopped.</p>
          </div>
        )}

        {session && p && (
          <div className="mt-4 space-y-3" aria-live="polite">
            <div>
              <div className="flex justify-between text-sm text-ink2">
                <span>
                  Signer {session.config.signerId}: {p.glossesDone} of {p.glossesTotal} signs complete
                </span>
                <span>
                  {p.takes} / {p.targetTakes} takes
                </span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-soft" role="progressbar" aria-label="Session progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
                <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
              </div>
            </div>

            {session.done ? (
              <p className="notice notice-good">Session complete: every sign has {session.config.takesPerGloss} saved takes.</p>
            ) : (
              <div className="rounded-2xl bg-surface2 p-4 text-center">
                <p className="text-sm uppercase tracking-wide text-ink2">Sign this</p>
                <p className="mt-1 break-words text-4xl font-bold">{gloss}</p>
                <p className="mt-2 text-sm text-ink2">
                  Take {Math.min((session.accepted[gloss!] ?? 0) + 1, session.config.takesPerGloss)} of {session.config.takesPerGloss}
                  {(session.attempts[gloss!] ?? 0) > 0 && `, ${session.attempts[gloss!]} attempt(s) so far`}
                </p>
                <p className="mt-2 text-sm text-ink2">Start with your hands down, sign once, then lower your hands. Both shoulders and your hands in view.</p>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <button className="btn btn-primary" disabled={!canRecord} onClick={() => void record()}>
                {recorder.phase.kind === "idle" ? `Record (3-2-1, ${seconds} s)` : recorder.phase.kind === "sending" ? "Saving…" : "Recording…"}
              </button>
              <button className={btn} disabled={recorder.busy || session.done} onClick={() => setSession((s) => (s ? skipGloss(s) : s))}>
                <SkipForward size={16} aria-hidden /> Skip this sign
              </button>
              <button className={btn} disabled={recorder.busy} onClick={() => setSession((s) => (s ? previousGloss(s) : s))}>
                <StepBack size={16} aria-hidden /> Previous sign
              </button>
              <button
                className={btn}
                disabled={recorder.busy}
                onClick={() => {
                  setSession(null);
                  setLast(null);
                }}
              >
                <SquareStop size={16} aria-hidden /> Stop session
              </button>
            </div>
            <p className="text-sm text-ink2">Keyboard (when not typing): {shortcutHelp(["record"])}.</p>

            {last?.error && <p role="alert" className="notice notice-bad">{last.error}</p>}
            {last?.result && !last.result.accepted && (
              <div className="notice notice-warn">
                <p className="font-semibold">Take of {last.gloss} rejected, not saved, not counted.</p>
                <ul className="mt-1 list-disc pl-5 text-sm">
                  {last.result.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
            {last?.result?.accepted && (
              <p className="notice notice-good">
                Saved a take of {last.gloss}: {last.result.stats.frames} frames in {last.result.stats.seconds}s, {last.result.stats.no_hand_frames} without a hand.
              </p>
            )}

            <ul className="flex flex-wrap gap-1 text-sm" aria-label="Signs in this session">
              {session.config.glosses.map((g, i) => {
                const n = session.accepted[g] ?? 0;
                const complete = n >= session.config.takesPerGloss;
                const current = !session.done && i === session.index;
                return (
                  <li key={g} className={`tag !px-3 !py-1 !text-sm ${current ? "bg-accent text-onaccent" : complete ? "bg-goodbg text-goodfg" : "bg-surface2 text-ink2"}`}>
                    {g} {n}/{session.config.takesPerGloss}
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
