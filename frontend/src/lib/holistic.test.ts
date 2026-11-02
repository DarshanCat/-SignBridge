import { describe, expect, it } from "vitest";
import { LOAD_PHASE_TEXT, USE_CPU_INFERENCE } from "./holistic";

describe("landmark loader settings", () => {
  it("uses CPU inference by default (GPU first frame measured at about 29 s)", () => {
    expect(USE_CPU_INFERENCE).toBe(true);
  });
  it("has a text for every loading phase", () => {
    for (const p of ["script", "initialize", "warmup", "ready"] as const) expect(LOAD_PHASE_TEXT[p].length).toBeGreaterThan(5);
  });
});
