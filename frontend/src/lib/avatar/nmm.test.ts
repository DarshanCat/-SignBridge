import { describe, expect, it } from "vitest";
import type { SignClip } from "./clip";
import { NMM_PARAMS, nmmEnvelope, nmmHeadOffset, withNmm } from "./nmm";
import { SequencePlayer } from "./player";

const mk = (gloss: string, duration = 2): SignClip => ({
  gloss,
  duration,
  source: { author: "t", license: "t", description: "t" },
  tracks: [{ bone: "upperArm_r", keyframes: [{ t: 0, rot: [-0.3, 0, 0] }, { t: duration, rot: [-0.3, 0, 0] }] }],
});

describe("non-manual head markers (rule-based approximation)", () => {
  it("eases in and out and is zero at the sentence edges", () => {
    expect(nmmEnvelope(0, 4)).toBe(0);
    expect(nmmEnvelope(4, 4)).toBe(0);
    expect(nmmEnvelope(2, 4)).toBe(1);
  });

  it("negation shakes the head about the vertical axis within a small amplitude", () => {
    const ys = Array.from({ length: 200 }, (_, i) => nmmHeadOffset(["negation"], i * 0.02, 4)[1]);
    expect(Math.max(...ys)).toBeGreaterThan(0.1);
    expect(Math.max(...ys.map(Math.abs))).toBeLessThanOrEqual(NMM_PARAMS.shakeAmp);
    expect(nmmHeadOffset(["negation"], 1, 4).slice(0, 3).filter((v, i) => i !== 1)).toEqual([0, 0]);
  });

  it("yes-no questions pitch forward and wh questions roll, both slightly", () => {
    expect(nmmHeadOffset(["yes-no-question"], 2, 4)).toEqual([NMM_PARAMS.yesNoPitch, 0, 0]);
    expect(nmmHeadOffset(["wh-question"], 2, 4)).toEqual([0, 0, NMM_PARAMS.whRoll]);
    expect(NMM_PARAMS.yesNoPitch).toBeLessThan(0.2);
    expect(NMM_PARAMS.whRoll).toBeLessThan(0.2);
  });

  it("only touches the head and ignores unknown tags", () => {
    const base = { upperArm_r: [1, 0, 0] as [number, number, number] };
    expect(withNmm(base, ["tense:past"], 2, 4)).toBe(base);
    const p = withNmm(base, ["wh-question"], 2, 4);
    expect(p.upperArm_r).toEqual([1, 0, 0]);
    expect(p.head).toEqual([0, 0, NMM_PARAMS.whRoll]);
  });

  it("the player adds the head offset while playing and not at rest", () => {
    const p = new SequencePlayer();
    p.load([mk("A"), mk("B")]);
    p.setNmm(["wh-question"]);
    expect(p.pose()).toEqual({});
    p.play();
    p.tick(2);
    expect(p.pose().head?.[2]).toBeCloseTo(NMM_PARAMS.whRoll);
    p.load([mk("A")]); // loading a new sentence clears the markers
    p.play();
    p.tick(0.5);
    expect(p.pose().head).toBeUndefined();
  });
});
