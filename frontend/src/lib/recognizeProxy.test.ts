import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "../app/api/signs/recognize/route";
import { LIVE_THRESHOLD, recognizeViaUpstream } from "./recognizeProxy";

const hand = Array.from({ length: 21 }, () => ({ x: 0.5, y: 0.5, z: 0 }));
const frames = [{ pose: null, left_hand: null, right_hand: hand }];
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const FORBIDDEN = ["label", "confidence", "alternatives", "gloss", "english", "accepted"];

function expectNoPrediction(body: object) {
  for (const k of FORBIDDEN) expect(Object.keys(body)).not.toContain(k);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("a failed upstream call never returns a label", () => {
  const failures: [string, typeof fetch][] = [
    ["the network is down", async () => { throw new TypeError("fetch failed"); }],
    ["the request times out", async () => { throw new DOMException("timed out", "TimeoutError"); }],
    ["the backend answers 500", async () => json({ detail: "boom" }, 500)],
    ["the backend answers 503 (no model)", async () => json({ detail: "no model" }, 503)],
    ["the backend answers 422", async () => json({ detail: "unusable" }, 422)],
    ["the answer is not JSON", async () => new Response("<html>bad gateway</html>", { status: 200 })],
    ["the answer has no predictions", async () => json({ predictions: [], accepted: false })],
    ["the answer has a malformed prediction", async () => json({ predictions: [{ label: 3, confidence: "high" }] })],
    ["the confidence is not a number", async () => json({ predictions: [{ label: "Hello", confidence: null }] })],
  ];
  for (const [name, fetchImpl] of failures) {
    it(`when ${name}`, async () => {
      const r = await recognizeViaUpstream(frames, "http://backend.test", fetchImpl);
      expect(r.ok).toBe(false);
      expect(r.status).toBeGreaterThanOrEqual(400);
      expectNoPrediction(r.body);
      expect(typeof (r.body as { detail: string }).detail).toBe("string");
    });
  }

  it("when no backend is configured", async () => {
    const fetchImpl = vi.fn();
    for (const base of [undefined, "", "   "]) {
      const r = await recognizeViaUpstream(frames, base, fetchImpl as unknown as typeof fetch);
      expect(r.ok).toBe(false);
      expect(r.status).toBe(503);
      expectNoPrediction(r.body);
    }
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("when the frames are missing or empty", async () => {
    for (const bad of [undefined, null, [], "frames", {}]) {
      const r = await recognizeViaUpstream(bad, "http://backend.test", vi.fn() as unknown as typeof fetch);
      expect(r.ok).toBe(false);
      expect(r.status).toBe(400);
      expectNoPrediction(r.body);
    }
  });
});

describe("the route", () => {
  const post = (body: unknown) => POST(new Request("http://localhost/api/signs/recognize", { method: "POST", body: typeof body === "string" ? body : JSON.stringify(body) }));

  it("answers 502 without a label when the upstream call fails", async () => {
    vi.stubEnv("SIGNBRIDGE_UPSTREAM_URL", "http://backend.test");
    vi.stubGlobal("fetch", async () => { throw new TypeError("fetch failed"); });
    const res = await post({ frames, commit: true, sign: "Hello" }); // a hint such as sign must never become the answer
    expect(res.status).toBe(502);
    expectNoPrediction(await res.json());
  });

  it("answers 503 without a label when no backend is configured", async () => {
    vi.stubEnv("SIGNBRIDGE_UPSTREAM_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    const res = await post({ frames });
    expect(res.status).toBe(503);
    expectNoPrediction(await res.json());
  });

  it("answers 400 without a label for a body that is not JSON", async () => {
    const res = await post("not json");
    expect(res.status).toBe(400);
    expectNoPrediction(await res.json());
  });
});

describe("a real answer is passed on, and only a real one", () => {
  it("accepts the label of the model above the live threshold", async () => {
    const fetchImpl = (async () => json({ predictions: [{ label: "Hat", confidence: 0.93 }, { label: "Cap", confidence: 0.03 }], num_frames_used: 20, gloss: ["HAT"], english: "The hat." })) as unknown as typeof fetch;
    const r = await recognizeViaUpstream(frames, "http://backend.test/", fetchImpl);
    expect(r.ok).toBe(true);
    expect(r.body).toMatchObject({ accepted: true, label: "Hat", gloss: "HAT", confidence: 0.93, num_frames_used: 20 });
  });

  it("applies the live threshold again: below it the answer is UNRECOGNIZED with no gloss", async () => {
    const fetchImpl = (async () => json({ predictions: [{ label: "Hat", confidence: LIVE_THRESHOLD - 0.01 }], gloss: ["HAT"], english: "The hat." })) as unknown as typeof fetch;
    const r = await recognizeViaUpstream(frames, "http://backend.test", fetchImpl);
    expect(r.body).toMatchObject({ accepted: false, label: "UNRECOGNIZED", gloss: null, english: "" });
  });

  it("calls the real endpoint with the frames and nothing else", async () => {
    const seen: { url: string; body: string }[] = [];
    const fetchImpl = (async (url: string, init: RequestInit) => {
      seen.push({ url, body: String(init.body) });
      return json({ predictions: [{ label: "Hat", confidence: 0.9 }] });
    }) as unknown as typeof fetch;
    await recognizeViaUpstream(frames, "http://backend.test", fetchImpl);
    expect(seen[0].url).toBe("http://backend.test/api/signs/translate");
    expect(JSON.parse(seen[0].body)).toEqual({ frames });
  });

  it("frames without any hand are not classified: no confidence, no alternatives, no network call", async () => {
    const fetchImpl = vi.fn();
    const r = await recognizeViaUpstream([{ pose: null, left_hand: null, right_hand: null }], "http://backend.test", fetchImpl as unknown as typeof fetch);
    expect(r.ok).toBe(true);
    expect(r.body).toMatchObject({ accepted: false, label: "UNRECOGNIZED", reason: "no_hands" });
    expect(Object.keys(r.body)).not.toContain("confidence");
    expect(Object.keys(r.body)).not.toContain("alternatives");
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
