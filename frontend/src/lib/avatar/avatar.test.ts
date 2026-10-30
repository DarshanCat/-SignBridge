import { describe, expect, it } from "vitest";
import { parseClip, sampleClip, type SignClip } from "./clip";
import { SequencePlayer } from "./player";
import { missingBones } from "./rig";
import { RIG_TEST_CLIP } from "./rigTest";

const clip = (gloss: string, duration = 1): SignClip => ({
  gloss,
  duration,
  source: { author: "t", license: "t", description: "t" },
  tracks: [{ bone: "upperArm_r", keyframes: [{ t: 0, rot: [0, 0, 0] }, { t: duration, rot: [-1, 0, 0] }] }],
});

describe("rig and clips", () => {
  it("rig contains every animatable bone", () => expect(missingBones()).toEqual([]));

  it("the rig self-test clip is a valid clip", () => expect(() => parseClip(RIG_TEST_CLIP)).not.toThrow());

  it("rejects malformed clips", () => {
    const bad = (m: (c: SignClip) => void) => {
      const c = structuredClone(clip("A"));
      m(c);
      return () => parseClip(c);
    };
    expect(bad((c) => (c.tracks[0].bone = "tail"))).toThrow(/unknown bone/);
    expect(bad((c) => (c.duration = 0))).toThrow(/duration/);
    expect(bad((c) => (c.tracks[0].keyframes[1].t = 9))).toThrow(/keyframe times/);
    expect(bad((c) => (c.tracks[0].keyframes[0].rot = [0, 0] as never))).toThrow(/rotation/);
    expect(bad((c) => (c.source.license = ""))).toThrow(/source/);
    expect(() => parseClip(null)).toThrow();
  });

  it("interpolates and clamps", () => {
    const c = clip("A");
    expect(sampleClip(c, 0.5).upperArm_r[0]).toBeCloseTo(-0.5);
    expect(sampleClip(c, 5).upperArm_r[0]).toBe(-1);
    expect(sampleClip(c, -1).upperArm_r[0]).toBe(0);
    expect(sampleClip(c, 0.5).head).toBeUndefined();
  });
});

describe("SequencePlayer", () => {
  const make = () => {
    const p = new SequencePlayer();
    p.load([clip("A", 1), clip("B", 2)]);
    return p;
  };

  it("does nothing with an empty playlist", () => {
    const p = new SequencePlayer();
    p.play();
    expect(p.snapshot().status).toBe("idle");
  });

  it("plays clips sequentially and finishes", () => {
    const p = make();
    p.play();
    p.tick(0.5);
    expect(p.snapshot()).toMatchObject({ status: "playing", index: 0, gloss: "A" });
    p.tick(0.75);
    expect(p.snapshot()).toMatchObject({ index: 1, gloss: "B" });
    p.tick(5);
    expect(p.snapshot().status).toBe("finished");
    expect(p.pose()).toEqual({});
  });

  it("pauses and resumes without advancing time", () => {
    const p = make();
    p.play();
    p.tick(0.4);
    p.pause();
    const before = p.pose().upperArm_r[0];
    p.tick(10);
    expect(p.pose().upperArm_r[0]).toBe(before);
    expect(p.snapshot().status).toBe("paused");
    p.play();
    expect(p.snapshot().status).toBe("playing");
  });

  it("replay restarts the current sign, restart restarts the sequence", () => {
    const p = make();
    p.play();
    p.tick(1.5);
    p.replay();
    expect(p.snapshot()).toMatchObject({ index: 1, status: "playing" });
    expect(p.pose().upperArm_r[0]).toBeCloseTo(0);
    p.restart();
    expect(p.snapshot().index).toBe(0);
  });

  it("play after finishing restarts; replay after finishing replays the last sign", () => {
    const p = make();
    p.play();
    p.tick(10);
    p.replay();
    expect(p.snapshot()).toMatchObject({ index: 1, status: "playing" });
    p.tick(10);
    p.play();
    expect(p.snapshot()).toMatchObject({ index: 0, status: "playing" });
  });

  it("respects playback rate and notifies subscribers", () => {
    const p = make();
    let calls = 0;
    p.subscribe(() => calls++);
    p.setRate(0.5);
    p.play();
    p.tick(1);
    expect(p.snapshot().index).toBe(0);
    expect(calls).toBeGreaterThan(0);
  });
});
