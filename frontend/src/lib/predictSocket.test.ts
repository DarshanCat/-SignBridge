import { describe, expect, it } from "vitest";
import { connectPredict, parsePredictMessage, predictUrl, type PredictChannel } from "./predictSocket";

function fake() {
  const sent: string[] = [];
  const closed = { v: false };
  const sock = {
    onmessage: null as ((e: { data: unknown }) => void) | null,
    onerror: null,
    onclose: null,
    send: (d: string) => sent.push(d),
    close: () => {
      closed.v = true;
    },
  };
  return { sock, sent, closed };
}

describe("prediction channel", () => {
  it("builds the ws url", () => {
    expect(predictUrl("http://127.0.0.1:8000")).toBe("ws://127.0.0.1:8000/ws/predict");
    expect(predictUrl("https://api.example.org/")).toBe("wss://api.example.org/ws/predict");
  });

  it("parses ready, prediction and errors; unknown messages are errors, never predictions", () => {
    const ready = parsePredictMessage(JSON.stringify({ type: "ready", classes: 266, architecture: "cnn", threshold: 0.6, threshold_source: "validation" }));
    expect(ready).toMatchObject({ type: "state", state: { kind: "ready", classes: 266, threshold: 0.6 } });
    expect(parsePredictMessage(JSON.stringify({ type: "prediction", accepted: true, label: "Hello", confidence: 0.9 })).type).toBe("prediction");
    expect(parsePredictMessage(JSON.stringify({ type: "error", error: "model_not_trained", message: "m" }))).toEqual({
      type: "state",
      state: { kind: "model_not_trained", message: "m" },
    });
    expect(parsePredictMessage(JSON.stringify({ type: "error", error: "bad_frames", message: "x" }))).toEqual({ type: "error", message: "x" });
    expect(parsePredictMessage("not json").type).toBe("error");
    expect(parsePredictMessage(JSON.stringify({ type: "mystery" })).type).toBe("error");
  });

  it("reports state, forwards predictions and sends predict and reset messages", () => {
    const states: PredictChannel[] = [];
    const preds: unknown[] = [];
    const { sock, sent, closed } = fake();
    const c = connectPredict("ws://x/ws/predict", { onState: (s) => states.push(s), onPrediction: (p) => preds.push(p) }, () => sock);
    sock.onmessage?.({ data: JSON.stringify({ type: "ready", classes: 3, architecture: "cnn", threshold: 0.5, threshold_source: "default" }) });
    sock.onmessage?.({ data: JSON.stringify({ type: "prediction", accepted: false, label: "UNRECOGNIZED", confidence: 0.2 }) });
    c.predict([{ pose: null }], true);
    c.reset();
    expect(states.map((s) => s.kind)).toEqual(["connecting", "ready"]);
    expect(preds).toHaveLength(1);
    expect(JSON.parse(sent[0])).toEqual({ type: "predict", frames: [{ pose: null }], commit: true });
    expect(JSON.parse(sent[1])).toEqual({ type: "reset" });
    c.close();
    expect(closed.v).toBe(true);
  });

  it("reports model_not_trained from the server and a failed connection", () => {
    const states: PredictChannel[] = [];
    const { sock } = fake();
    connectPredict("ws://x", { onState: (s) => states.push(s) }, () => sock);
    sock.onmessage?.({ data: JSON.stringify({ type: "error", error: "model_not_trained", message: "No model." }) });
    expect(states[1]).toEqual({ kind: "model_not_trained", message: "No model." });
    const failed: PredictChannel[] = [];
    connectPredict("ws://x", { onState: (s) => failed.push(s) }, () => {
      throw new Error("blocked");
    });
    expect(failed[1].kind).toBe("unavailable");
  });

  it("parses the continuous mode events and sends frames, undo and flush", () => {
    const signEv = parsePredictMessage(JSON.stringify({ type: "sign", accepted: true, label: "Hello", segment: { start: 3, end: 30, frames: 28 }, sequence: ["HELLO"], english: "Hello." }));
    expect(signEv).toMatchObject({ type: "sign", sign: { label: "Hello", segment: { frames: 28 } } });
    expect(parsePredictMessage(JSON.stringify({ type: "stream", active: true, frames_seen: 40, sequence: [], english: "" }))).toMatchObject({ type: "stream", status: { active: true } });
    expect(parsePredictMessage(JSON.stringify({ type: "sequence", removed: "HELLO", sequence: [], english: "" }))).toMatchObject({ type: "sequence", update: { removed: "HELLO" } });
    const seen: string[] = [];
    const { sock, sent } = fake();
    const c = connectPredict("ws://x", { onState: () => {}, onSign: (s) => seen.push(s.label), onStream: (s) => seen.push(String(s.active)), onSequence: (u) => seen.push(`seq${u.sequence.length}`) }, () => sock);
    sock.onmessage?.({ data: JSON.stringify({ type: "sign", label: "Hello" }) });
    sock.onmessage?.({ data: JSON.stringify({ type: "stream", active: false, frames_seen: 1, sequence: [], english: "" }) });
    sock.onmessage?.({ data: JSON.stringify({ type: "sequence", sequence: [], english: "" }) });
    c.frames([{ pose: null }]);
    c.undo();
    c.flush();
    expect(seen).toEqual(["Hello", "false", "seq0"]);
    expect(sent.map((x) => JSON.parse(x).type)).toEqual(["frames", "undo", "flush"]);
  });
});
