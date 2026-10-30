import { describe, expect, it } from "vitest";
import { BONES, type SignClip } from "./clip";
import { blendPoses, SequencePlayer, TRANSITION_S } from "./player";
import { RIG } from "./rig";
import { validateRig, validateSkeletonNames } from "./skeleton";

const mk = (gloss: string, rot: number, duration = 1): SignClip => ({
  gloss,
  duration,
  source: { author: "t", license: "t", description: "t" },
  tracks: [{ bone: "upperArm_r", keyframes: [{ t: 0, rot: [rot, 0, 0] }, { t: duration, rot: [rot, 0, 0] }] }],
});

describe("player: stop, reset, dispose and transitions", () => {
  it("stop rewinds but keeps the playlist; reset unloads", () => {
    const p = new SequencePlayer();
    p.load([mk("A", -1), mk("B", -1)]);
    p.play();
    p.tick(1.5);
    p.stop();
    expect(p.snapshot()).toMatchObject({ status: "idle", index: 0, total: 2 });
    expect(p.pose()).toEqual({});
    p.play();
    expect(p.snapshot().status).toBe("playing");
    p.reset();
    expect(p.snapshot()).toMatchObject({ status: "idle", total: 0, gloss: null });
  });

  it("blends from the end of one sign into the next, then settles", () => {
    const p = new SequencePlayer();
    p.load([mk("A", -1), mk("B", 0)]);
    p.play();
    p.tick(1 + TRANSITION_S / 2); // half-way through the blend into B
    expect(p.snapshot().gloss).toBe("B");
    expect(p.pose().upperArm_r[0]).toBeCloseTo(-0.5, 1);
    p.tick(TRANSITION_S);
    expect(p.pose().upperArm_r[0]).toBeCloseTo(0);
  });

  it("blendPoses treats missing bones as rest; dispose drops subscribers", () => {
    expect(blendPoses({ head: [1, 0, 0] }, {}, 0.5).head[0]).toBeCloseTo(0.5);
    const p = new SequencePlayer();
    let calls = 0;
    p.subscribe(() => calls++);
    p.dispose();
    p.load([mk("A", 0)]);
    expect(calls).toBe(0);
  });

  it("keeps clip order for the current gloss", () => {
    const p = new SequencePlayer();
    p.load([mk("A", 0), mk("B", 0), mk("C", 0)]);
    p.play();
    const seen: (string | null)[] = [p.snapshot().gloss];
    for (let i = 0; i < 3; i++) {
      p.tick(1);
      seen.push(p.snapshot().gloss);
    }
    expect(seen).toEqual(["A", "B", "C", "C"]);
  });
});

describe("skeleton validation", () => {
  const base = { offset: [0, 0, 0] as [number, number, number] };

  it("accepts the shipped rig", () => expect(validateRig(RIG)).toEqual([]));

  it("detects missing parents, duplicates, cycles and missing bones", () => {
    expect(validateRig([{ ...base, name: "a", parent: "ghost" }], ["a"])).toEqual(
      expect.arrayContaining([expect.stringMatching(/unknown parent/), expect.stringMatching(/exactly one root/)]),
    );
    expect(validateRig([{ ...base, name: "a", parent: null }, { ...base, name: "a", parent: null }], [])).toContain(
      "duplicate bone names",
    );
    expect(
      validateRig([{ ...base, name: "r", parent: null }, { ...base, name: "x", parent: "y" }, { ...base, name: "y", parent: "x" }], []),
    ).toEqual(expect.arrayContaining([expect.stringMatching(/unreachable/)]));
    expect(validateRig([{ ...base, name: "r", parent: null }], ["head"])).toEqual(["missing required bone head"]);
  });

  it("checks imported node names against the required bones", () => {
    expect(validateSkeletonNames(BONES).ok).toBe(true);
    expect(validateSkeletonNames(["head"]).missing).toContain("hand_l.index");
  });
});
