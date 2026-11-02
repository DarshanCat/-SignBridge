import { describe, expect, it } from "vitest";
import { appendFrame, EMPTY_BUFFER, MAX_MISSING_POSE, pushFrame, summarize, toFrame, yScaleFor, type BufferState, type LandmarkFrame } from "./landmarks";

const empty: LandmarkFrame = { pose: null, left_hand: null, right_hand: null };

describe("landmarks", () => {
  it("maps missing parts to null and defaults z", () => {
    const f = toFrame({ poseLandmarks: [{ x: 1, y: 2 } as never], leftHandLandmarks: [] });
    expect(f.pose).toEqual([{ x: 1, y: 2, z: 0 }]);
    expect(f.left_hand).toBeNull();
    expect(f.right_hand).toBeNull();
  });

  it("keeps only the newest frames", () => {
    let buf: LandmarkFrame[] = [];
    for (let i = 0; i < 5; i++) buf = pushFrame(buf, { ...empty, pose: [{ x: i, y: 0, z: 0 }] }, 3);
    expect(buf).toHaveLength(3);
    expect(buf[0].pose?.[0].x).toBe(2);
  });

  it("summarizes pose and hand presence", () => {
    const p = [{ x: 0, y: 0, z: 0 }];
    const s = summarize([{ ...empty, pose: p }, { ...empty, pose: p, left_hand: p }, empty]);
    expect(s).toEqual({ frames: 3, withPose: 2, withHands: 1 });
  });

  describe("appendFrame", () => {
    const withPose: LandmarkFrame = { ...empty, pose: [{ x: 0, y: 0, z: 0 }] };

    it("never grows beyond the cap", () => {
      let st: BufferState = EMPTY_BUFFER;
      for (let i = 0; i < 500; i++) st = appendFrame(st, withPose, 60);
      expect(st.frames).toHaveLength(60);
    });

    it("clears a stale sequence once tracking is lost for too long", () => {
      let st: BufferState = EMPTY_BUFFER;
      for (let i = 0; i < 20; i++) st = appendFrame(st, withPose);
      for (let i = 0; i < MAX_MISSING_POSE; i++) st = appendFrame(st, empty);
      expect(st.frames.length).toBeGreaterThan(0); // brief dropout keeps the sequence
      st = appendFrame(st, empty);
      expect(st.frames).toEqual([]);
    });

    it("starts a fresh sequence after recovery and resets the missing streak", () => {
      let st: BufferState = EMPTY_BUFFER;
      for (let i = 0; i < MAX_MISSING_POSE + 5; i++) st = appendFrame(st, empty);
      st = appendFrame(st, withPose);
      expect(st).toEqual({ frames: [withPose], missingStreak: 0 });
    });
  });
});

describe("aspect correction", () => {
  const r = { poseLandmarks: [{ x: 0.4, y: 0.5, z: 0.1 }], rightHandLandmarks: [{ x: 0.6, y: 0.3, z: -0.2 }] };

  it("leaves a 16:9 image untouched", () => {
    const f = toFrame(r, 16 / 9);
    expect(f.pose?.[0]).toEqual({ x: 0.4, y: 0.5, z: 0.1 });
  });

  it("stretches y by 4/3 for a 4:3 webcam and never touches x or z", () => {
    const f = toFrame(r, 4 / 3);
    expect(f.pose?.[0].x).toBe(0.4);
    expect(f.pose?.[0].z).toBe(0.1);
    expect(f.pose?.[0].y).toBeCloseTo(0.5 * (4 / 3));
    expect(f.right_hand?.[0].y).toBeCloseTo(0.3 * (4 / 3));
  });

  it("falls back to no scaling for an unusable aspect", () => {
    expect(yScaleFor(0)).toBe(1);
    expect(yScaleFor(Number.NaN)).toBe(1);
    expect(yScaleFor(16 / 9)).toBeCloseTo(1);
  });
});
