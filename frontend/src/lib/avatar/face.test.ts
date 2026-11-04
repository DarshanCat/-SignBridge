import { describe, expect, it } from "vitest";
import type { SignClip } from "./clip";
import { Blinker, ExpressionSmoother, FACE, nmmFaceTargets } from "./face";
import { SequencePlayer } from "./player";

const run = (seed: number, seconds: number, dt = 1 / 60) => {
  const b = new Blinker(seed);
  const w: number[] = [];
  for (let t = 0; t < seconds; t += dt) w.push(b.step(dt));
  return w;
};

/** Blink starts: the weight rises from 0. */
const blinkStarts = (w: number[], dt = 1 / 60): number[] => {
  const out: number[] = [];
  for (let i = 1; i < w.length; i++) if (w[i - 1] === 0 && w[i] > 0) out.push(i * dt);
  return out;
};

describe("blinking", () => {
  it("is deterministic for a seed and different for another", () => {
    expect(run(7, 20)).toEqual(run(7, 20));
    expect(run(7, 20)).not.toEqual(run(8, 20));
  });

  it("stays within 0..1, closes fully and opens again", () => {
    const w = run(1, 30);
    expect(Math.min(...w)).toBe(0);
    expect(Math.max(...w)).toBe(1);
    expect(w.every((x) => x >= 0 && x <= 1)).toBe(true);
    expect(w[w.length - 1]).toBeGreaterThanOrEqual(0);
  });

  it("blinks at a natural rate: one blink every 2.6 to 6 s, with an occasional quick second blink", () => {
    const starts = blinkStarts(run(3, 300));
    const gaps = starts.slice(1).map((s, i) => s - starts[i]);
    expect(starts.length).toBeGreaterThan(40); // about 300 s / 4.3 s, plus double blinks
    expect(starts.length).toBeLessThan(120);
    const long = gaps.filter((g) => g > 1);
    expect(Math.min(...long)).toBeGreaterThanOrEqual(FACE.blinkGapS[0] - 0.05);
    expect(Math.max(...long)).toBeLessThanOrEqual(FACE.blinkGapS[1] + 0.9); // a double blink adds up to one blink length plus its gap
    expect(gaps.some((g) => g < 1)).toBe(true); // double blinks happen
  });

  it("one blink lasts about a quarter of a second", () => {
    const w = run(5, 12);
    const i = w.findIndex((x) => x > 0);
    let j = i;
    while (w[j] > 0) j++;
    const dur = (j - i) / 60;
    expect(dur).toBeGreaterThan(0.15);
    expect(dur).toBeLessThan(0.4);
  });
});

describe("non-manual markers on the face (rule-based approximations)", () => {
  const total = 4;
  it("is all zero when nothing plays or no marker is set", () => {
    expect(nmmFaceTargets(null)).toEqual({ surprised: 0, sad: 0 });
    expect(nmmFaceTargets({ tags: [], t: 2, total })).toEqual({ surprised: 0, sad: 0 });
    expect(nmmFaceTargets({ tags: ["wh-question"], t: 2, total })).toEqual({ surprised: 0, sad: 0 }); // wh keeps only the head tilt
  });

  it("yes-no questions raise the brows (surprised) and negation frowns (sad), each alone", () => {
    const yn = nmmFaceTargets({ tags: ["yes-no-question"], t: 2, total });
    expect(yn.surprised).toBeCloseTo(FACE.yesNoSurprised, 5);
    expect(yn.sad).toBe(0);
    const neg = nmmFaceTargets({ tags: ["negation"], t: 2, total });
    expect(neg.sad).toBeCloseTo(FACE.negationFrown, 5);
    expect(neg.surprised).toBe(0);
  });

  it("eases in and out with the same envelope as the head movement and stays at a small weight", () => {
    const edge = nmmFaceTargets({ tags: ["negation"], t: 0, total });
    expect(edge.sad).toBe(0);
    expect(nmmFaceTargets({ tags: ["negation"], t: total, total }).sad).toBe(0);
    expect(nmmFaceTargets({ tags: ["negation"], t: 0.15, total }).sad).toBeGreaterThan(0);
    expect(FACE.yesNoSurprised).toBeLessThanOrEqual(0.5);
    expect(FACE.negationFrown).toBeLessThanOrEqual(0.5);
  });

  it("the player reports the marker state only while a sentence plays", () => {
    const clip: SignClip = { gloss: "A", duration: 2, source: { author: "t", license: "t", description: "t" }, tracks: [] };
    const p = new SequencePlayer();
    p.load([clip]);
    p.setNmm(["negation"]);
    expect(p.nmmState()).toBeNull(); // idle
    p.play();
    p.tick(0.5);
    expect(p.nmmState()).toEqual({ tags: ["negation"], t: 0.5, total: 2 });
    p.tick(5);
    expect(p.nmmState()).toBeNull(); // finished
  });
});

describe("expression smoothing", () => {
  it("moves toward the target without overshoot and is nearly frame-rate independent", () => {
    const at = (dt: number) => {
      const s = new ExpressionSmoother();
      let v = { surprised: 0, sad: 0 };
      for (let t = 0; t < 0.5; t += dt) {
        v = s.step({ surprised: 0.4, sad: 0 }, dt);
        expect(v.surprised).toBeLessThanOrEqual(0.4);
      }
      return v.surprised;
    };
    expect(at(1 / 30)).toBeCloseTo(at(1 / 120), 1);
    expect(at(1 / 60)).toBeGreaterThan(0.3);
  });
});
