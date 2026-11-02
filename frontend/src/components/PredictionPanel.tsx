"use client";
import { Eraser, ScanSearch, Undo2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { API_URL } from "@/lib/api";
import { FrameQueue } from "@/lib/frameQueue";
import { shortcutHelp } from "@/lib/shortcuts";
import { BUFFER_FRAMES, type LandmarkFrame } from "@/lib/landmarks";
import {
  connectPredict,
  predictUrl,
  type LivePrediction,
  type LiveSign,
  type PredictChannel,
  type PredictClient,
  type SequenceUpdate,
  type StreamStatus,
} from "@/lib/predictSocket";
import { useShortcuts } from "./useShortcuts";

const CHUNK_MS = 250;

interface LogEntry {
  id: number;
  accepted: boolean;
  text: string;
}

/**
 * Module A prediction panel: the landmark buffer, the state of the live prediction WebSocket, and the recognized signs.
 * Without a trained model it says "Model not trained" and never shows a prediction. Below the threshold the result is "Unrecognized".
 * Two modes: one isolated sign per button press, or continuous signing where the server finds the start and end of every sign
 * (hands down or still between signs) and the sentence builds up by itself. Only landmarks are sent, never video.
 */
export function PredictionPanel({
  running,
  runId,
  bufferFrames,
  getBuffer,
  setFrameListener,
}: {
  running: boolean;
  runId: number;
  bufferFrames: number;
  getBuffer: () => LandmarkFrame[];
  setFrameListener: (fn: ((frame: LandmarkFrame, tMs: number) => void) | null) => void;
}) {
  const [channel, setChannel] = useState<{ runId: number; value: PredictChannel } | null>(null);
  const [result, setResult] = useState<{ runId: number; value: LivePrediction } | null>(null);
  const [problem, setProblem] = useState<{ runId: number; message: string } | null>(null);
  const [waiting, setWaiting] = useState(false);
  const [continuous, setContinuous] = useState(false);
  const [stream, setStream] = useState<{ runId: number; value: StreamStatus } | null>(null);
  const [log, setLog] = useState<LogEntry[]>([]);
  const client = useRef<PredictClient | null>(null);
  const nextId = useRef(1);

  useEffect(() => {
    if (!running) return;
    const c = connectPredict(predictUrl(API_URL), {
      onState: (value) => {
        if (value.kind !== "connecting") setChannel({ runId, value });
      },
      onPrediction: (value) => {
        setWaiting(false);
        setProblem(null);
        setResult({ runId, value });
      },
      onSign: (s: LiveSign) => {
        const pct = (s.confidence * 100).toFixed(0);
        setLog((l) => [...l.slice(-5), { id: nextId.current++, accepted: s.accepted, text: s.accepted ? `${s.gloss} (${pct}%)` : `Unrecognized sign (best guess ${pct}%)` }]);
      },
      onStream: (value: StreamStatus) => setStream({ runId, value }),
      onSequence: (u: SequenceUpdate) => setStream((s) => ({ runId, value: { active: false, frames_seen: s?.value.frames_seen ?? 0, sequence: u.sequence, english: u.english } })),
      onError: (message) => {
        setWaiting(false);
        setProblem({ runId, message });
      },
    });
    client.current = c;
    return () => {
      client.current = null;
      c.close();
    };
  }, [running, runId]);

  const current: PredictChannel = running
    ? channel && channel.runId === runId
      ? channel.value
      : { kind: "connecting" }
    : { kind: "idle" };
  const ready = current.kind === "ready";

  // continuous mode: queue every extracted frame and send them every 250 ms; closing the mode closes a sign that is still open
  useEffect(() => {
    if (!running || !ready || !continuous) return;
    const q = new FrameQueue<LandmarkFrame>(300);
    setFrameListener((f) => q.push(f));
    const timer = setInterval(() => {
      const chunk = q.drain();
      if (chunk.length) client.current?.frames(chunk);
    }, CHUNK_MS);
    return () => {
      clearInterval(timer);
      setFrameListener(null);
      const chunk = q.drain();
      if (chunk.length) client.current?.frames(chunk);
      client.current?.flush();
    };
  }, [running, ready, continuous, setFrameListener]);

  const shown = running && result && result.runId === runId ? result.value : null;
  const err = running && problem && problem.runId === runId ? problem.message : null;
  const st = running && stream && stream.runId === runId ? stream.value : null;
  const pct = Math.min(100, Math.round((bufferFrames / BUFFER_FRAMES) * 100));
  const btn = "inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm disabled:opacity-40";

  useShortcuts({
    undo: ready && continuous && st?.sequence.length ? () => client.current?.undo() : undefined,
    clear: ready ? clearAll : undefined,
    record: ready && !continuous && bufferFrames > 0 && !waiting ? recognize : undefined,
  });

  function recognize() {
    setWaiting(true);
    setProblem(null);
    client.current?.predict(getBuffer(), true);
  }
  function clearAll() {
    client.current?.reset();
    setResult(null);
    setStream(null);
    setLog([]);
  }

  return (
    <div className="mt-4 rounded-lg border border-white/10 p-3" aria-label="Live prediction">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Live prediction</h3>
      <div className="mt-2" aria-label="Landmark buffer">
        <div className="flex justify-between text-xs text-slate-400">
          <span>Landmark buffer</span>
          <span>
            {bufferFrames} / {BUFFER_FRAMES} frames
          </span>
        </div>
        <div className="mt-1 h-2 overflow-hidden rounded bg-white/10" role="progressbar" aria-valuemin={0} aria-valuemax={BUFFER_FRAMES} aria-valuenow={bufferFrames}>
          <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div aria-live="polite" className="mt-3 rounded-lg bg-white/5 p-3 text-sm">
        {current.kind === "idle" && <p className="text-slate-400">Start the camera to open the live prediction channel.</p>}
        {current.kind === "connecting" && <p className="text-slate-400">Connecting to the live prediction channel…</p>}
        {current.kind === "model_not_trained" && (
          <>
            <p className="font-semibold text-amber-300">Model not trained</p>
            <p className="mt-1 text-xs text-slate-300">{current.message} Landmarks are buffered locally only; no sign, gloss, confidence score or English text is produced.</p>
          </>
        )}
        {current.kind === "not_implemented" && <p className="font-semibold text-amber-300">{current.message}</p>}
        {current.kind === "unavailable" && (
          <p className="text-amber-300">
            {current.message} Is the backend running? Start it with scripts\serve.ps1, then stop and start the camera.
          </p>
        )}
        {current.kind === "ready" && (
          <p className="text-xs text-slate-400">
            Model ready: {current.classes} classes ({current.architecture}). Signs below {Math.round(current.threshold * 100)}% confidence are shown as
            unrecognized (threshold from {current.thresholdSource === "validation" ? "the validation split" : "the default setting"}).
          </p>
        )}
      </div>

      {ready && (
        <div className="mt-3 space-y-3">
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" checked={continuous} onChange={(e) => setContinuous(e.target.checked)} className="mt-1" />
            <span>
              Continuous signing
              <span className="block text-xs text-slate-400">
                The server detects each sign from your hand movement. Lower your hands (or hold them still) between signs. Signs signed back to
                back without a pause cannot be separated.
              </span>
            </span>
          </label>

          {continuous ? (
            <div className="space-y-2" aria-live="polite">
              <p className={`text-sm ${st?.active ? "text-emerald-300" : "text-slate-300"}`}>
                {st?.active ? "Signing…" : "Resting. Sign now, then lower your hands."}
              </p>
              <div className="flex flex-wrap gap-2">
                {(st?.sequence ?? []).map((g, i) => (
                  <span key={`${g}-${i}`} className="rounded bg-sky-400/20 px-2 py-0.5 text-xs text-sky-200">
                    {g}
                  </span>
                ))}
                {!st?.sequence.length && <span className="text-xs text-slate-500">No signs yet.</span>}
              </div>
              {st?.english && <p className="text-base font-medium">{st.english}</p>}
              <div className="flex flex-wrap gap-2">
                <button className={btn} onClick={() => client.current?.undo()} disabled={!st?.sequence.length}>
                  <Undo2 size={16} aria-hidden /> Undo last sign
                </button>
                <button className={btn} onClick={clearAll}>
                  <Eraser size={16} aria-hidden /> Clear
                </button>
              </div>
              {log.length > 0 && (
                <ul className="text-xs text-slate-400" aria-label="Recent signs">
                  {log.map((e) => (
                    <li key={e.id} className={e.accepted ? "text-slate-300" : "text-amber-300"}>
                      {e.text}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={recognize}
                  disabled={bufferFrames === 0 || waiting}
                  className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-ink disabled:opacity-40"
                >
                  <ScanSearch size={16} aria-hidden /> {waiting ? "Recognizing…" : "Recognize sign"}
                </button>
                <button onClick={clearAll} className={btn}>
                  <Eraser size={16} aria-hidden /> Clear sentence
                </button>
              </div>
              <p className="text-xs text-slate-400">Recognizes one isolated sign from the last ~2 seconds of landmarks.</p>
              {shown && (
                <div aria-live="polite" className="space-y-1 text-sm">
                  {shown.accepted ? (
                    <p className="text-emerald-300">
                      {shown.label} ({(shown.confidence * 100).toFixed(1)}%) as gloss {shown.gloss}
                    </p>
                  ) : (
                    <p className="text-amber-300">
                      Unrecognized: best guess has only {(shown.confidence * 100).toFixed(1)}% confidence, below the {Math.round(shown.threshold * 100)}% threshold.
                    </p>
                  )}
                  <ul className="text-xs text-slate-300">
                    {shown.alternatives.map((a) => (
                      <li key={a.label}>
                        {a.label}: {(a.confidence * 100).toFixed(1)}%
                      </li>
                    ))}
                  </ul>
                  {shown.sequence.length > 0 && (
                    <>
                      <p className="text-xs text-slate-400">Gloss sequence: {shown.sequence.join(" ")}</p>
                      <p className="text-base font-medium">{shown.english}</p>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
          <p className="text-xs text-slate-500">Keyboard (when not typing): {shortcutHelp(continuous ? ["undo", "clear"] : ["record", "clear"])}. In this panel R recognizes the buffered sign.</p>
          {err && <p className="text-sm text-rose-300">{err}</p>}
        </div>
      )}
    </div>
  );
}
