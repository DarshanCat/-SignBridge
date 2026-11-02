"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { apiPost, type RecordResult } from "@/lib/api";
import { buildRecordRequest, countdownSteps, type RecordOptions } from "@/lib/recorder";
import type { LandmarkCapture } from "./useLandmarkCapture";

export type TakePhase = { kind: "idle" } | { kind: "countdown"; n: number } | { kind: "recording"; left: number } | { kind: "sending" };

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export interface TakeOutcome {
  result: RecordResult | null;
  error: string | null;
}

/**
 * One recorded take: 3-2-1 countdown, a fixed number of seconds of landmarks (never video), then the quality checked save on the server.
 * Returns null when the take was cancelled (for example the panel closed during the countdown).
 */
export function useTakeRecorder(capture: LandmarkCapture) {
  const { beginRecording, endRecording } = capture;
  const [phase, setPhase] = useState<TakePhase>({ kind: "idle" });
  const cancelled = useRef(false);

  useEffect(
    () => () => {
      cancelled.current = true;
    },
    [],
  );

  const cancel = useCallback(() => {
    cancelled.current = true;
  }, []);

  const recordTake = useCallback(
    async (gloss: string, seconds: number, opts: RecordOptions = {}): Promise<TakeOutcome | null> => {
      cancelled.current = false;
      for (const n of countdownSteps()) {
        setPhase({ kind: "countdown", n });
        await sleep(1000);
        if (cancelled.current) {
          setPhase({ kind: "idle" });
          return null;
        }
      }
      beginRecording();
      const t0 = performance.now();
      const total = seconds * 1000;
      while (performance.now() - t0 < total) {
        setPhase({ kind: "recording", left: Math.ceil((total - (performance.now() - t0)) / 1000) });
        await sleep(100);
        if (cancelled.current) {
          endRecording();
          setPhase({ kind: "idle" });
          return null;
        }
      }
      const frames = endRecording();
      const elapsed = performance.now() - t0;
      setPhase({ kind: "sending" });
      try {
        const result = await apiPost<RecordResult>("/api/record/sign", buildRecordRequest(gloss, frames, elapsed, opts));
        return { result, error: null };
      } catch (e) {
        return { result: null, error: e instanceof Error ? e.message : "Saving the take failed." };
      } finally {
        setPhase({ kind: "idle" });
      }
    },
    [beginRecording, endRecording],
  );

  return { phase, recordTake, cancel, busy: phase.kind !== "idle" };
}
