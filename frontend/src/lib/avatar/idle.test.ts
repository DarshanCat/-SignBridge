import { describe, expect, it } from "vitest";
import { Euler, Quaternion } from "three";
import type { Pose } from "./clip";
import { IDLE, PoseSmoother, restWeight, slerpEuler, smoothstep, withRelaxedRest } from "./idle";
import { blendPoses } from "./player";

const quat = (e: [number, number, number]) => new Quaternion().setFromEuler(new Euler(e[0], e[1], e[2], "XYZ"));

describe("relaxed rest layer", () => {
  it("returns all 20 bones and relaxes a hanging arm: slight angle out, elbow bend, curled and fanned fingers", () => {
    const { pose, spread } = withRelaxedRest({}, 0);
    expect(Object.keys(pose)).toHaveLength(20);
    expect(pose.upperArm_l[2]).toBeCloseTo(IDLE.armOut);
    expect(pose.upperArm_r[2]).toBeCloseTo(-IDLE.armOut); // mirrored
    expect(pose.foreArm_r[0]).toBeCloseTo(-IDLE.elbowBend);
    expect(pose["hand_l.pinky"][0]).toBeLessThan(pose["hand_l.index"][0]); // little finger curls more
    expect(spread["hand_l.index"]).toBeGreaterThan(0);
    expect(spread["hand_r.index"]).toBeLessThan(0);
  });

  it("leaves a lifted arm exactly as the clip has it (the sign is not edited)", () => {
    const raised: Pose = { upperArm_r: [-1.2, 0.1, -0.2], foreArm_r: [-1.1, 0, 0.3], "hand_r.index": [-0.7, 0, 0] };
    expect(restWeight(raised, "r")).toBe(0);
    const { pose, spread } = withRelaxedRest(raised, 3.7);
    expect(pose.upperArm_r).toEqual(raised.upperArm_r);
    expect(pose.foreArm_r).toEqual(raised.foreArm_r);
    expect(pose["hand_r.index"]).toEqual(raised["hand_r.index"]);
    expect(spread["hand_r.index"]).toBeCloseTo(0);
    expect(restWeight(raised, "l")).toBe(1); // the other arm still rests
  });

  it("fades the relaxed offsets in gradually while an arm is lowered", () => {
    const w = [0, 0.05, 0.15, 0.25, 0.4, 0.6].map((lift) => restWeight({ upperArm_l: [lift, 0, 0] }, "l"));
    for (let i = 1; i < w.length; i++) expect(w[i]).toBeLessThanOrEqual(w[i - 1]);
    expect(w[0]).toBe(1);
    expect(w[w.length - 1]).toBe(0);
  });

  it("breathing and sway stay tiny and move over time", () => {
    const a = withRelaxedRest({}, 0).pose.chest[0];
    const b = withRelaxedRest({}, 1.1).pose.chest[0];
    expect(a).not.toBeCloseTo(b, 4);
    for (let t = 0; t < 30; t += 0.7) {
      const p = withRelaxedRest({}, t).pose;
      expect(Math.abs(p.chest[0])).toBeLessThanOrEqual(IDLE.breathChest + 1e-9);
      expect(Math.abs(p.spine[2])).toBeLessThanOrEqual(IDLE.swaySpine + 1e-9);
      expect(Math.abs(p.head[1])).toBeLessThanOrEqual(IDLE.driftHead + 1e-9);
    }
  });
});

describe("smoothing", () => {
  it("slerp goes through the middle rotation and is an identity at 0 and 1", () => {
    const a: [number, number, number] = [0.2, 0, 0];
    const b: [number, number, number] = [-1.4, 0.6, 0.3];
    expect(quat(slerpEuler(a, b, 0)).angleTo(quat(a))).toBeLessThan(1e-6);
    expect(quat(slerpEuler(a, b, 1)).angleTo(quat(b))).toBeLessThan(1e-6);
    const half = quat(slerpEuler(a, b, 0.5));
    expect(half.angleTo(quat(a))).toBeCloseTo(quat(a).angleTo(quat(b)) / 2, 5);
  });

  it("blendPoses uses quaternion slerp for body bones and plain interpolation for finger curls", () => {
    const out = blendPoses({ head: [0, 0, 0], "hand_r.index": [-1, 0, 0] }, { head: [0, 2, 0], "hand_r.index": [0, 0, 0] }, 0.5);
    expect(out.head[1]).toBeCloseTo(1);
    expect(out["hand_r.index"][0]).toBeCloseTo(-0.5);
  });

  it("smoothstep eases in and out", () => {
    expect(smoothstep(0)).toBe(0);
    expect(smoothstep(1)).toBe(1);
    expect(smoothstep(0.1)).toBeLessThan(0.1);
    expect(smoothstep(0.9)).toBeGreaterThan(0.9);
  });

  it("the smoother never snaps: a jump in the target is followed over several frames, at any frame rate", () => {
    const rest = withRelaxedRest({}, 0);
    const up: Pose = { ...rest.pose, upperArm_r: [-1.5, 0, 0], foreArm_r: [-1.2, 0, 0] };
    for (const fps of [30, 60, 144]) {
      const s = new PoseSmoother(0.07);
      s.step(rest.pose, rest.spread, 1 / fps);
      let prev = rest.pose.upperArm_r[0];
      const dt = 1 / fps;
      let t = 0;
      let biggest = 0;
      while (t < 0.5) {
        const x = s.step(up, rest.spread, dt).pose.upperArm_r[0];
        biggest = Math.max(biggest, Math.abs(x - prev));
        prev = x;
        t += dt;
      }
      const distance = Math.abs(-1.5 - rest.pose.upperArm_r[0]);
      expect(biggest).toBeLessThan(distance * (1 - Math.exp(-dt / 0.07)) * 1.05); // the first frame moves only a fraction of the jump
      expect(biggest).toBeLessThan(distance * 0.5);
      expect(prev).toBeLessThan(-1.4); // and it arrives
    }
  });

  it("the first step takes the target (no ramp from nothing)", () => {
    const s = new PoseSmoother();
    const r = s.step({ head: [0.3, 0, 0], "hand_l.index": [-0.4, 0, 0] }, { "hand_l.index": 0.1 }, 0.016);
    expect(r.pose.head[0]).toBeCloseTo(0.3);
    expect(r.pose["hand_l.index"][0]).toBeCloseTo(-0.4);
    expect(r.spread["hand_l.index"]).toBeCloseTo(0.1);
  });
});

describe("reduced motion (calm idle)", () => {
  it("switches off breathing, sway and head drift but keeps the relaxed hands", () => {
    const calm = withRelaxedRest({}, 3.3, true);
    const lively = withRelaxedRest({}, 3.3, false);
    for (const bone of ["spine", "chest", "neck", "head"]) expect(calm.pose[bone]).toEqual([0, 0, 0]);
    expect(lively.pose.chest).not.toEqual([0, 0, 0]);
    expect(calm.pose["hand_l.index"]).toEqual(lively.pose["hand_l.index"]);
    expect(calm.pose.foreArm_l).toEqual(lively.pose.foreArm_l);
  });

  it("is constant over time", () => {
    expect(withRelaxedRest({}, 0, true)).toEqual(withRelaxedRest({}, 41.7, true));
  });
});
