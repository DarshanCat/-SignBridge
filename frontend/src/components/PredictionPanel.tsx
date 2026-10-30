"use client";
import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { BUFFER_FRAMES } from "@/lib/landmarks";
import { connectPredict, predictUrl, type PredictChannel } from "@/lib/predictSocket";

/**
 * Module A prediction panel. It shows the landmark buffer and the state of the live prediction WebSocket. The server is a stub until a
 * model is trained, so this panel states "model not trained" and never shows a prediction, gloss, or confidence.
 */
export function PredictionPanel({ running, runId, bufferFrames }: { running: boolean; runId: number; bufferFrames: number }) {
  const [channel, setChannel] = useState<{ runId: number; value: PredictChannel } | null>(null);

  useEffect(() => {
    if (!running) return;
    return connectPredict(predictUrl(API_URL), (value) => {
      if (value.kind !== "connecting") setChannel({ runId, value });
    });
  }, [running, runId]);

  const current = running ? (channel && channel.runId === runId ? channel.value : ({ kind: "connecting" } as PredictChannel)) : ({ kind: "idle" } as PredictChannel);
  const pct = Math.min(100, Math.round((bufferFrames / BUFFER_FRAMES) * 100));

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
        {current.kind === "not_implemented" && (
          <>
            <p className="font-semibold text-amber-300">Live prediction not implemented</p>
            <p className="mt-1 text-xs text-slate-300">{current.message}</p>
          </>
        )}
        {current.kind === "unavailable" && <p className="text-amber-300">{current.message}</p>}
      </div>
    </div>
  );
}
