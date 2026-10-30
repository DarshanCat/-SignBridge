import { describe, expect, it } from "vitest";
import { buildRecordRequest, countdownSteps, isValidGloss, measureFps, normalizeGloss } from "./recorder";

const frame = { pose: null, left_hand: null, right_hand: null };

describe("recorder helpers", () => {
  it("normalises and validates glosses like the backend", () => {
    expect(normalizeGloss(" good morning ")).toBe("GOOD-MORNING");
    expect(isValidGloss("water")).toBe(true);
    for (const bad of ["", "   ", "../x", "a/b", "-x", "A".repeat(40)]) expect(isValidGloss(bad)).toBe(false);
  });

  it("measures the achieved frame rate and guards against empty takes", () => {
    expect(measureFps(90, 3000)).toBe(30);
    expect(measureFps(0, 3000)).toBe(0);
    expect(measureFps(10, 0)).toBe(0);
  });

  it("builds a landmarks only request", () => {
    const body = buildRecordRequest("my sign", [frame, frame, frame], 1000);
    expect(body).toEqual({ gloss: "MY-SIGN", fps: 3, frames: [frame, frame, frame] });
    expect(Object.keys(body).sort()).toEqual(["fps", "frames", "gloss"]);
  });

  it("counts down 3, 2, 1", () => {
    expect(countdownSteps()).toEqual([3, 2, 1]);
  });
});
