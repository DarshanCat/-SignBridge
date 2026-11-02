"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL } from "@/lib/api";
import { FrameQueue } from "@/lib/frameQueue";
import type { LandmarkFrame } from "@/lib/landmarks";
import { connectPredict, predictUrl, type LiveSign, type PredictChannel, type PredictClient, type StreamStatus } from "@/lib/predictSocket";
import type { LandmarkCapture } from "./useLandmarkCapture";

const CHUNK_MS = 250;
const MAX_LOG = 6;

export interface SignLogEntry {
  id: number;
  accepted: boolean;
  text: string;
}

export interface ContinuousSigning {
  channel: PredictChannel;
  ready: boolean;
  /** True while a sign is being signed (the server sees raised, moving hands). */
  signing: boolean;
  sequence: string[];
  english: string;
  log: SignLogEntry[];
  error: string | null;
  undo: () => void;
  clear: () => void;
}

/**
 * Continuous sign recognition on the live prediction socket: while the camera runs, every extracted frame is queued and sent every 250 ms;
 * the server finds each sign and returns the running gloss sequence and English sentence. Landmarks only, never video.
 */
export function useContinuousSigning(capture: LandmarkCapture, enabled: boolean): ContinuousSigning {
  const { state, runId, setFrameListener } = capture;
  const running = state === "running";
  const [channel, setChannel] = useState<{ runId: number; value: PredictChannel } | null>(null);
  const [stream, setStream] = useState<{ runId: number; value: StreamStatus } | null>(null);
  const [log, setLog] = useState<SignLogEntry[]>([]);
  const [error, setError] = useState<{ runId: number; message: string } | null>(null);
  const client = useRef<PredictClient | null>(null);
  const nextId = useRef(1);

  useEffect(() => {
    if (!running) return;
    const c = connectPredict(predictUrl(API_URL), {
      onState: (value) => {
        if (value.kind !== "connecting") setChannel({ runId, value });
      },
      onSign: (s: LiveSign) => {
        const pct = (s.confidence * 100).toFixed(0);
        setLog((l) => [...l.slice(-(MAX_LOG - 1)), { id: nextId.current++, accepted: s.accepted, text: s.accepted ? `${s.gloss} (${pct}%)` : `Unrecognized sign (best guess ${pct}%)` }]);
      },
      onStream: (value) => setStream({ runId, value }),
      onSequence: (u) => setStream((s) => ({ runId, value: { active: false, frames_seen: s?.value.frames_seen ?? 0, sequence: u.sequence, english: u.english } })),
      onError: (message) => setError({ runId, message }),
    });
    client.current = c;
    return () => {
      client.current = null;
      c.close();
    };
  }, [running, runId]);

  const current: PredictChannel = running ? (channel && channel.runId === runId ? channel.value : { kind: "connecting" }) : { kind: "idle" };
  const ready = current.kind === "ready";

  useEffect(() => {
    if (!running || !ready || !enabled) return;
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
  }, [running, ready, enabled, setFrameListener]);

  const st = running && stream && stream.runId === runId ? stream.value : null;
  const err = running && error && error.runId === runId ? error.message : null;
  const undo = useCallback(() => client.current?.undo(), []);
  const clear = useCallback(() => {
    client.current?.reset();
    setStream(null);
    setLog([]);
  }, []);

  return { channel: current, ready, signing: !!st?.active, sequence: st?.sequence ?? [], english: st?.english ?? "", log, error: err, undo, clear };
}
