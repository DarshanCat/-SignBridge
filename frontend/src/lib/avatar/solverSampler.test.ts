import { describe, expect, it } from "vitest";
import { blendSolved, bodyWeight } from "./solverSampler";
import type { SignClip } from "./clip";
import type { Solved } from "./retarget";

const clip = { gloss: "A", duration: 2, tracks: [], source: { author: "t", license: "t", description: "t" }, landmarks: { version: 1, t: [0.25, 1, 1.75], pose_idx: [], pose: [], left: [], right: [] } } as unknown as SignClip;

describe("solver sampler", () => {
  it("is 0 at the rest ends, 1 in the body of the sign and fades between", () => {
    expect(bodyWeight(clip, 0)).toBe(0);
    expect(bodyWeight(clip, 1)).toBe(1);
    expect(bodyWeight(clip, 2)).toBe(0);
    expect(bodyWeight(clip, 0.125)).toBeGreaterThan(0);
    expect(bodyWeight(clip, 0.125)).toBeLessThan(1);
    expect(bodyWeight({ ...clip, landmarks: undefined } as SignClip, 1)).toBe(0);
  });

  it("expresses the clip's finger curl per joint and cross-fades it with the solved joints", () => {
    const legacy = { "hand_l.index": [-1, 0, 0] as [number, number, number] };
    const solved = { pose: { "hand_l.index#1": [-0.2, 0, 0.1] as [number, number, number] }, arm: { l: true, r: false }, hand: { l: true, r: false }, wrist: { l: null, r: null } } as unknown as Solved;
    const half = blendSolved(legacy, solved, 0.5);
    expect(half["hand_l.index"]).toBeUndefined(); // the single curl is replaced by per joint rotations
    expect(half["hand_l.index#2"]).toBeDefined();
    expect(half["hand_l.index#1"][0]).toBeCloseTo((-0.4 * 0.5 + -0.2 * 0.5) , 5);
    expect(blendSolved(legacy, solved, 1)["hand_l.index#1"]).toEqual([-0.2, 0, 0.1]);
    expect(blendSolved(legacy, solved, 0)["hand_l.index#1"][2]).toBe(0);
  });
});
