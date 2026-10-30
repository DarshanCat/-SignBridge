/** Client for the backend live prediction WebSocket (/ws/predict). The server is currently a stub that never produces a prediction. */

export type PredictChannel =
  | { kind: "idle" }
  | { kind: "connecting" }
  | { kind: "model_not_trained"; message: string }
  | { kind: "not_implemented"; message: string }
  | { kind: "unavailable"; message: string };

export const PREDICT_PATH = "/ws/predict";

export function predictUrl(apiUrl: string): string {
  return apiUrl.replace(/^http/i, "ws").replace(/\/$/, "") + PREDICT_PATH;
}

/** Interpret one server message. Anything that is not a recognised error is reported as unavailable; no prediction is invented. */
export function parsePredictMessage(raw: unknown): PredictChannel {
  try {
    const m = JSON.parse(String(raw)) as { type?: string; error?: string; message?: string };
    if (m.type === "error" && m.error === "model_not_trained") {
      return { kind: "model_not_trained", message: m.message ?? "No trained sign recognition model is available." };
    }
    if (m.type === "error" && m.error === "not_implemented") {
      return { kind: "not_implemented", message: m.message ?? "Live streaming prediction is not implemented yet." };
    }
  } catch {
    // fall through
  }
  return { kind: "unavailable", message: "The live prediction channel sent a message this client does not understand." };
}

interface SocketLike {
  onmessage: ((e: { data: unknown }) => void) | null;
  onerror: (() => void) | null;
  onclose: (() => void) | null;
  close(): void;
}

/** Open the channel once and report its state. Returns a function that closes it. */
export function connectPredict(
  url: string,
  onState: (s: PredictChannel) => void,
  make: (url: string) => SocketLike = (u) => new WebSocket(u) as unknown as SocketLike,
): () => void {
  let settled = false;
  const settle = (s: PredictChannel) => {
    settled = true;
    onState(s);
  };
  onState({ kind: "connecting" });
  let ws: SocketLike;
  try {
    ws = make(url);
  } catch {
    settle({ kind: "unavailable", message: "Could not open the live prediction channel." });
    return () => {};
  }
  ws.onmessage = (e) => settle(parsePredictMessage(e.data));
  ws.onerror = () => {
    if (!settled) settle({ kind: "unavailable", message: "Could not reach the live prediction channel." });
  };
  ws.onclose = () => {
    if (!settled) settle({ kind: "unavailable", message: "The live prediction channel closed without a message." });
  };
  return () => {
    ws.onmessage = ws.onerror = ws.onclose = null;
    ws.close();
  };
}
