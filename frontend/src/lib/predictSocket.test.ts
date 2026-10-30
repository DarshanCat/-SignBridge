import { describe, expect, it } from "vitest";
import { connectPredict, parsePredictMessage, predictUrl, type PredictChannel } from "./predictSocket";

describe("prediction channel", () => {
  it("builds the ws url", () => {
    expect(predictUrl("http://localhost:8000")).toBe("ws://localhost:8000/ws/predict");
    expect(predictUrl("https://api.example.org/")).toBe("wss://api.example.org/ws/predict");
  });

  it("recognises the stub's errors and never invents a prediction", () => {
    const stub = JSON.stringify({ type: "error", error: "model_not_trained", message: "No trained model." });
    expect(parsePredictMessage(stub)).toEqual({ kind: "model_not_trained", message: "No trained model." });
    expect(parsePredictMessage(JSON.stringify({ type: "error", error: "not_implemented" })).kind).toBe("not_implemented");
    expect(parsePredictMessage(JSON.stringify({ type: "prediction", label: "HELLO" })).kind).toBe("unavailable");
    expect(parsePredictMessage("not json").kind).toBe("unavailable");
  });

  it("reports the state from a fake socket and closes cleanly", () => {
    const states: PredictChannel[] = [];
    let closed = false;
    const sock = { onmessage: null as ((e: { data: unknown }) => void) | null, onerror: null, onclose: null, close: () => (closed = true) };
    const stop = connectPredict("ws://x/ws/predict", (s) => states.push(s), () => sock);
    sock.onmessage?.({ data: JSON.stringify({ type: "error", error: "model_not_trained", message: "m" }) });
    expect(states.map((s) => s.kind)).toEqual(["connecting", "model_not_trained"]);
    stop();
    expect(closed).toBe(true);
  });

  it("reports a failed connection", () => {
    const states: PredictChannel[] = [];
    connectPredict("ws://x", (s) => states.push(s), () => {
      throw new Error("blocked");
    });
    expect(states[1].kind).toBe("unavailable");
  });
});
