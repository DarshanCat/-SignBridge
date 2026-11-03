/** Client for the backend live prediction WebSocket (/ws/predict). */

export type PredictChannel =
  | { kind: "idle" }
  | { kind: "connecting" }
  | { kind: "ready"; classes: number; architecture: string; threshold: number; thresholdSource: string }
  | { kind: "model_not_trained"; message: string }
  | { kind: "not_implemented"; message: string }
  | { kind: "unavailable"; message: string };

export interface LivePrediction {
  accepted: boolean;
  /** The class label, or "UNRECOGNIZED" when the confidence is below the threshold. */
  label: string;
  gloss: string | null;
  confidence: number;
  threshold: number;
  alternatives: { label: string; confidence: number }[];
  sequence: string[];
  english: string;
  num_frames_used: number;
}

export const PREDICT_PATH = "/ws/predict";

/** WebSocket URL of the live recognizer: NEXT_PUBLIC_WS_URL if set (full URL including /ws/predict), otherwise the API URL with http turned into ws. */
export function predictUrl(apiUrl: string, override: string | undefined = process.env.NEXT_PUBLIC_WS_URL): string {
  if (override && override.trim()) return override.trim();
  if (!apiUrl || !apiUrl.trim()) return "wss://cat9141-signbridge-api.hf.space/ws/predict";
  return apiUrl.replace(/^http/i, "ws").replace(/\/$/, "") + PREDICT_PATH;
}

export interface StreamStatus {
  active: boolean;
  frames_seen: number;
  sequence: string[];
  english: string;
}

/** A sign found by the segmenter on the stream: a prediction plus where it was in the stream (usable frame numbers). */
export interface LiveSign extends LivePrediction {
  segment: { start: number; end: number; frames: number };
}

export interface SequenceUpdate {
  removed?: string | null;
  sequence: string[];
  english: string;
}

export type ServerEvent =
  | { type: "state"; state: PredictChannel }
  | { type: "prediction"; prediction: LivePrediction }
  | { type: "sign"; sign: LiveSign }
  | { type: "stream"; status: StreamStatus }
  | { type: "sequence"; update: SequenceUpdate }
  | { type: "error"; message: string }
  | { type: "ignored" };

/** Interpret one server message. Anything not recognised is reported as an error; no prediction is ever invented. */
export function parsePredictMessage(raw: unknown): ServerEvent {
  try {
    const m = JSON.parse(String(raw)) as Record<string, unknown>;
    switch (m.type) {
      case "ready":
        return {
          type: "state",
          state: {
            kind: "ready",
            classes: Number(m.classes),
            architecture: String(m.architecture),
            threshold: Number(m.threshold),
            thresholdSource: String(m.threshold_source),
          },
        };
      case "prediction":
        return { type: "prediction", prediction: m as unknown as LivePrediction };
      case "sign":
        return { type: "sign", sign: m as unknown as LiveSign };
      case "stream":
        return { type: "stream", status: m as unknown as StreamStatus };
      case "sequence":
        return { type: "sequence", update: m as unknown as SequenceUpdate };
      case "ignored":
      case "reset_ok":
        return { type: "ignored" };
      case "error": {
        const message = typeof m.message === "string" ? m.message : "The server reported an error.";
        if (m.error === "model_not_trained") return { type: "state", state: { kind: "model_not_trained", message } };
        if (m.error === "not_implemented") return { type: "state", state: { kind: "not_implemented", message } };
        return { type: "error", message };
      }
    }
  } catch {
    // fall through
  }
  return { type: "error", message: "The live prediction channel sent a message this client does not understand." };
}

interface SocketLike {
  onmessage: ((e: { data: unknown }) => void) | null;
  onerror: (() => void) | null;
  onclose: (() => void) | null;
  send(data: string): void;
  close(): void;
}

export interface PredictClient {
  /** Recognize one sign from landmark frames (landmarks only, no video). */
  predict(frames: unknown[], commit?: boolean): void;
  /** Clear the sentence built from earlier signs (and the segmenter). */
  reset(): void;
  /** Continuous mode: send a chunk of stream frames (up to 300). Finished signs come back as `sign` events. */
  frames(frames: unknown[]): void;
  /** Remove the last recognized sign from the sentence. */
  undo(): void;
  /** Close a sign that is still open. */
  flush(): void;
  close(): void;
}

export interface PredictHandlers {
  onState: (s: PredictChannel) => void;
  onPrediction?: (p: LivePrediction) => void;
  onSign?: (s: LiveSign) => void;
  onStream?: (s: StreamStatus) => void;
  onSequence?: (u: SequenceUpdate) => void;
  onError?: (message: string) => void;
}

/** Open the channel and report its state and results. Falls back seamlessly to HTTP REST when WebSocket is blocked. */
export function connectPredict(
  url: string,
  h: PredictHandlers,
  make: (url: string) => SocketLike = (u) => new WebSocket(u) as unknown as SocketLike,
): PredictClient {
  let settled = false;
  let useHttp = false;
  const localSequence: string[] = [];
  let pendingFrames: unknown[] = [];
  let framesSeen = 0;

  const settle = (s: PredictChannel) => {
    settled = true;
    h.onState(s);
  };

  const tryHttpFallback = (errMsg: string) => {
    if (typeof window !== "undefined" && typeof fetch === "function") {
      fetch("/api/model/status")
        .then((r) => r.json())
        .then((data) => {
          if (data && (data.state === "loaded" || data.status === "ok")) {
            useHttp = true;
            settle({
              kind: "ready",
              classes: data.classes ?? 262,
              architecture: String(data.architecture ?? "cnn").toUpperCase(),
              threshold: 0.7,
              thresholdSource: "validation",
            });
            return;
          }
          settle({ kind: "unavailable", message: errMsg });
        })
        .catch(() => {
          settle({ kind: "unavailable", message: errMsg });
        });
    } else {
      settle({ kind: "unavailable", message: errMsg });
    }
  };

  h.onState({ kind: "connecting" });
  let ws: SocketLike | null = null;
  try {
    ws = make(url);
  } catch {
    tryHttpFallback("Could not open the live prediction channel.");
  }
  if (ws) {
    ws.onmessage = (e) => {
      const ev = parsePredictMessage(e.data);
      if (ev.type === "state") settle(ev.state);
      else if (ev.type === "prediction") h.onPrediction?.(ev.prediction);
      else if (ev.type === "sign") h.onSign?.(ev.sign);
      else if (ev.type === "stream") h.onStream?.(ev.status);
      else if (ev.type === "sequence") h.onSequence?.(ev.update);
      else if (ev.type === "error") h.onError?.(ev.message);
    };
    ws.onerror = () => {
      if (!settled) tryHttpFallback("Could not reach the live prediction channel.");
    };
    ws.onclose = () => {
      if (!settled) tryHttpFallback("The live prediction channel closed without a message.");
    };
  }
  const send = (o: unknown) => ws?.send(JSON.stringify(o));
  return {
    predict: (frames, commit = true) => {
      if (useHttp) {
        fetch("/api/signs/recognize", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ frames, commit }),
        })
          .then((r) => r.json())
          .then((pred) => {
            if (pred) {
              h.onPrediction?.(pred);
              if (commit && pred.accepted && pred.label && pred.label !== "UNRECOGNIZED") {
                localSequence.push(pred.gloss || pred.label.toUpperCase());
                h.onSequence?.({ sequence: [...localSequence], english: localSequence.join(" ") });
              }
            }
          })
          .catch((err) => {
            h.onError?.(err instanceof Error ? err.message : "Inference request failed.");
          });
        return;
      }
      send({ type: "predict", frames, commit });
    },
    reset: () => {
      if (useHttp) {
        localSequence.length = 0;
        pendingFrames = [];
        h.onSequence?.({ sequence: [], english: "" });
        return;
      }
      send({ type: "reset" });
    },
    frames: (frames) => {
      if (useHttp) {
        framesSeen += frames.length;
        const hasHands = (frames as Array<{ left_hand?: unknown; right_hand?: unknown }>).some(
          (f) =>
            f &&
            ((Array.isArray(f.left_hand) && f.left_hand.length > 0) ||
              (Array.isArray(f.right_hand) && f.right_hand.length > 0))
        );
        if (hasHands) {
          pendingFrames.push(...frames);
          if (pendingFrames.length >= 32) {
            const batch = pendingFrames.splice(0, 48);
            fetch("/api/signs/recognize", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ frames: batch, commit: true }),
            })
              .then((r) => r.json())
              .then((pred) => {
                if (pred && pred.accepted && pred.label !== "UNRECOGNIZED") {
                  localSequence.push(pred.gloss || pred.label.toUpperCase());
                  h.onSign?.({
                    ...pred,
                    segment: { start: Math.max(0, framesSeen - 48), end: framesSeen, frames: batch.length },
                  });
                  h.onStream?.({
                    active: true,
                    frames_seen: framesSeen,
                    sequence: [...localSequence],
                    english: localSequence.join(" "),
                  });
                }
              })
              .catch(() => {});
          }
        } else {
          h.onStream?.({
            active: false,
            frames_seen: framesSeen,
            sequence: [...localSequence],
            english: localSequence.join(" "),
          });
        }
        return;
      }
      send({ type: "frames", frames });
    },
    undo: () => {
      if (useHttp) {
        const removed = localSequence.pop() || null;
        h.onSequence?.({ removed, sequence: [...localSequence], english: localSequence.join(" ") });
        return;
      }
      send({ type: "undo" });
    },
    flush: () => {
      if (useHttp) return;
      send({ type: "flush" });
    },
    close: () => {
      if (!ws) return;
      ws.onmessage = ws.onerror = ws.onclose = null;
      ws.close();
    },
  };
}
