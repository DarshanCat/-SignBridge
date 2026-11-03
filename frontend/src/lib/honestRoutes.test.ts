import { afterEach, describe, expect, it, vi } from "vitest";
import { GET as healthGet } from "../app/api/health/route";
import { GET as statusGet } from "../app/api/model/status/route";
import signRegistry from "../config/sign_registry.json";
import { computeRegistry, planFromClips } from "./registryReport";
import { proxyGet } from "./upstreamProxy";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("health and model status never answer on their own", () => {
  const failures: [string, typeof fetch][] = [
    ["the backend is down", async () => { throw new TypeError("fetch failed"); }],
    ["the backend times out", async () => { throw new DOMException("t", "TimeoutError"); }],
    ["the backend answers 500", async () => json({ detail: "boom" }, 500)],
    ["the answer is not JSON", async () => new Response("bad gateway", { status: 200 })],
    ["the answer is a list", async () => json([1, 2, 3])],
  ];
  for (const [name, fetchImpl] of failures) {
    it(`when ${name}: an error and none of the healthy fields`, async () => {
      for (const path of ["/api/health", "/api/model/status"]) {
        const r = await proxyGet(path, "http://backend.test", fetchImpl);
        expect(r.status).toBeGreaterThanOrEqual(400);
        for (const k of ["status", "state", "loaded", "classes", "model_path", "service"]) expect(Object.keys(r.body)).not.toContain(k);
        expect(typeof r.body.detail).toBe("string");
      }
    });
  }

  it("without a configured backend: 503, no network call", async () => {
    const fetchImpl = vi.fn();
    for (const base of [undefined, "", "  "]) {
      const r = await proxyGet("/api/health", base, fetchImpl as unknown as typeof fetch);
      expect(r.status).toBe(503);
      expect(Object.keys(r.body)).not.toContain("status");
    }
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("passes the real answer through", async () => {
    const r = await proxyGet("/api/model/status", "http://backend.test/", (async (url: string) => {
      expect(url).toBe("http://backend.test/api/model/status");
      return json({ state: "not_trained", loaded: false, classes: 0 });
    }) as unknown as typeof fetch);
    expect(r).toEqual({ status: 200, body: { state: "not_trained", loaded: false, classes: 0 } });
  });

  it("the routes: an unreachable backend gives an error, not ok and not loaded", async () => {
    vi.stubEnv("SIGNBRIDGE_UPSTREAM_URL", "http://backend.test");
    vi.stubGlobal("fetch", async () => { throw new TypeError("fetch failed"); });
    for (const route of [healthGet, statusGet]) {
      const res = await route();
      expect(res.status).toBe(502);
      const body = await res.json();
      expect(JSON.stringify(body)).not.toMatch(/"(ok|loaded)"/);
      expect(body.status).toBeUndefined();
      expect(body.state).toBeUndefined();
    }
  });

  it("the routes: no backend configured gives 503", async () => {
    vi.stubEnv("SIGNBRIDGE_UPSTREAM_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    expect((await healthGet()).status).toBe(503);
    expect((await statusGet()).status).toBe(503);
  });
});

describe("registry status is computed from files and review flags only", () => {
  const signs = [
    { gloss: "HELLO", asset_id: "hello.json", visually_reviewed: false, signer_reviewed: false },
    { gloss: "DOCTOR", asset_id: "doctor.json", visually_reviewed: true, signer_reviewed: true },
    { gloss: "WHERE", asset_id: null },
    { gloss: "BOOK", asset_id: "book.json", visually_reviewed: true, signer_reviewed: false },
  ];

  it("an empty clips folder means every registered asset is missing, none is present", () => {
    const r = computeRegistry(signs, []);
    expect(r.signs.map((s) => s.status)).toEqual(["missing_asset", "missing_asset", "no_clip", "missing_asset"]);
    expect(r.totals.verified).toBe(0);
  });

  it("verified needs the file and both review flags", () => {
    const r = computeRegistry(signs, ["hello", "doctor", "book", "water"]);
    expect(r.signs.map((s) => s.status)).toEqual(["clip_unreviewed", "verified", "no_clip", "clip_unreviewed"]);
    expect(r.totals).toMatchObject({ verified: 1, clip_unreviewed: 2, no_clip: 1, signs: 4 });
    expect(r.unregistered_clips).toEqual(["water"]);
  });

  it("a registry that claims verified without evidence is flagged", () => {
    const r = computeRegistry([{ gloss: "X", asset_id: "x.json", verification_status: "verified" }], ["x"]);
    expect(r.signs[0].status).toBe("clip_unreviewed");
    expect(r.signs[0].problems.join(" ")).toMatch(/claims verified/);
  });

  it("the shipped registry config marks no sign as reviewed by a signer (no clip is signer reviewed)", () => {
    const reviewed = (signRegistry.signs as { gloss: string; signer_reviewed?: boolean; visually_reviewed?: boolean; verification_status?: string }[]).filter(
      (s) => s.signer_reviewed || s.visually_reviewed || s.verification_status === "verified" || s.verification_status === "signer_reviewed",
    );
    expect(reviewed.map((s) => s.gloss)).toEqual([]);
  });
});

describe("the avatar plan counts only clips that exist", () => {
  it("a registered asset without a file is not available", () => {
    const r = planFromClips(["hello", "water", "go"], ["hello"]);
    expect(r.steps.map((s) => s.available)).toEqual([true, false, false]);
    expect(r.steps[0].clip_url).toBe("/animations/hello.json");
    expect(r.steps[1].clip_url).toBeNull();
    expect(r.missing).toEqual(["WATER", "GO"]);
    expect(r.message).toMatch(/2 of 3/);
  });

  it("nothing is playable without clips", () => {
    const r = planFromClips(["hello"], []);
    expect(r.playable).toBe(false);
    expect(r.message).toMatch(/nothing can be played/);
  });
});
