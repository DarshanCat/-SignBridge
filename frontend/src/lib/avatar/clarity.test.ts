import { describe, expect, it } from "vitest";
import { parseClip, type ClipLandmarks, type SignClip } from "./clip";
import { DEFAULT_SIGN_RATE, SequencePlayer } from "./player";
import { HOLD_S, peakTime } from "./peak";
import { SOURCE_ASPECT_Y, sourceFrame, sourceFrameAtTime } from "./sourceLandmarks";
import { bodyWeight } from "./solverSampler";

const POSE_IDX = [0, 2, 5, 9, 10, 11, 12, 13, 14, 15, 16];
const XS = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.02, 1.04, 1.3, 1.6, 1.9, 2.2]; // the right wrist: fast, nearly still at frame 6, fast again
const hand = (wx: number, wy: number): number[][] => Array.from({ length: 21 }, (_, k) => [wx + 0.01 * k, wy + 0.02 * k, 0.1 * k]);

/** A synthetic sample (not a dataset clip): only the right hand is present, 0.1 s between frames. */
function landmarks(xs = XS, handFrames: boolean[] = xs.map(() => true)): ClipLandmarks {
  return {
    version: 1,
    t: xs.map((_, i) => 0.3 + 0.1 * i),
    pose_idx: POSE_IDX,
    pose: xs.map((x) => POSE_IDX.map((idx) => (idx === 16 ? [x, 0.5, 0] : [0.5, 0.5 + 0.01 * idx, 0]))),
    left: xs.map(() => null),
    right: xs.map((x, i) => (handFrames[i] ? hand(x + 0.3, 0.9) : null)),
  };
}
const clipWith = (lm?: ClipLandmarks, duration = 2): SignClip => ({
  gloss: "TEST",
  duration,
  source: { author: "t", license: "t", description: "t" },
  tracks: [{ bone: "upperArm_r", keyframes: [{ t: 0, rot: [0, 0, 0] }, { t: duration, rot: [0, 0, 0] }] }],
  ...(lm ? { landmarks: lm } : {}),
});

describe("peak of a sign", () => {
  it("is the slowest moment of the hand in the middle of the sign", () => {
    const lm = landmarks();
    expect(peakTime(clipWith(lm))).toBeCloseTo(lm.t[6], 9);
  });
  it("is null without landmarks, with too few frames or when the hand hardly moves", () => {
    expect(peakTime(clipWith())).toBeNull();
    expect(peakTime(clipWith(landmarks(XS.slice(0, 5))))).toBeNull();
    expect(peakTime(clipWith(landmarks(XS.map(() => 0.5))))).toBeNull();
  });
});

describe("player: hold at the peak, phase, seek, default speed", () => {
  const lm = landmarks();
  const play = (): SequencePlayer => {
    const p = new SequencePlayer();
    p.load([clipWith(lm)]);
    p.play();
    return p;
  };
  it("defaults to 0.75x", () => expect(DEFAULT_SIGN_RATE).toBe(0.75));
  it("stands still at the peak for HOLD_S of clip time, then continues, and the sign ends later by that much", () => {
    const p = play();
    const peak = peakTime(clipWith(lm))!;
    while (p.current()!.time < peak - 1e-9) p.tick(0.01);
    expect(p.current()!.time).toBeCloseTo(peak, 6);
    p.tick(HOLD_S - 0.01);
    expect(p.current()!.time).toBeCloseTo(peak, 6); // still held
    p.tick(0.05);
    expect(p.current()!.time).toBeGreaterThan(peak + 0.02);
    let elapsed = 0;
    const q = play();
    while (q.snapshot().status === "playing") {
      q.tick(0.01);
      elapsed += 0.01;
    }
    expect(elapsed).toBeCloseTo(2 + HOLD_S, 1);
  });
  it("is in the sign phase between the first and last source frame and in transition outside", () => {
    const p = play();
    expect(p.phase()).toBe("transition");
    p.seek(0, 0.8);
    expect(p.phase()).toBe("sign");
    p.seek(0, 1.9);
    expect(p.phase()).toBe("transition");
    expect(new SequencePlayer().phase()).toBe("rest");
  });
  it("seek pauses, clamps the time and skips the hold", () => {
    const p = play();
    p.seek(5, 99);
    expect(p.snapshot().status).toBe("paused");
    expect(p.current()).toMatchObject({ index: 0, time: 2 });
    p.seek(0, -1);
    expect(p.current()!.time).toBe(0);
  });
  it("seek is ignored with nothing loaded", () => {
    const p = new SequencePlayer();
    p.seek(0, 1);
    expect(p.current()).toBeNull();
  });
});

describe("source landmarks", () => {
  const lm = landmarks();
  it("corrects the 16:9 picture aspect of vertical distances and flips to rig axes", () => {
    const f = sourceFrame(lm, 0);
    // pose point 16 is at image y 0.5; the nose (idx 0) at 0.5 + 0.0: both y = -0.5 * 9/16
    expect(f.wrist.r.y).toBeCloseTo(-0.5 * SOURCE_ASPECT_Y, 9);
    expect(f.mouth.y - f.nose.y).toBeCloseTo(-(0.095 - 0) * SOURCE_ASPECT_Y, 9); // mouth idx 9 and 10 average 0.595, nose 0.5
  });
  it("re-anchors the hand points at the pose wrist and keeps their offsets (depth flipped)", () => {
    const f = sourceFrame(lm, 0);
    const h = f.hand.r!;
    expect(h[0].distanceTo(f.wrist.r)).toBeCloseTo(0, 9);
    expect(h[4].x - h[0].x).toBeCloseTo(0.04, 9);
    expect(h[4].y - h[0].y).toBeCloseTo(-0.08 * SOURCE_ASPECT_Y, 9);
    expect(h[4].z - h[0].z).toBeCloseTo(-0.4, 9);
    expect(f.hand.l).toBeNull();
  });
  it("interpolates between frames and counts a hand as present only if it is in both", () => {
    const part = landmarks(XS, XS.map((_, i) => i !== 2));
    const mid = sourceFrameAtTime(part, (part.t[1] + part.t[2]) / 2);
    expect(mid.hand.r).toBeNull();
    const ok = sourceFrameAtTime(lm, (lm.t[3] + lm.t[4]) / 2);
    expect(ok.wrist.r.x).toBeCloseTo((XS[3] + XS[4]) / 2, 9);
    expect(ok.hand.r).not.toBeNull();
    expect(sourceFrameAtTime(lm, -5).wrist.r.x).toBeCloseTo(XS[0], 9);
    expect(sourceFrameAtTime(lm, 99).wrist.r.x).toBeCloseTo(XS[XS.length - 1], 9);
  });
});

describe("body weight of the retarget", () => {
  const clip = clipWith(landmarks());
  it("is 0 at the rest ends and 1 inside the sign; 0 for a clip without landmarks", () => {
    expect(bodyWeight(clip, 0)).toBe(0);
    expect(bodyWeight(clip, 0.8)).toBe(1);
    expect(bodyWeight(clip, 2)).toBeCloseTo(0, 9);
    expect(bodyWeight(clip, 0.15)).toBeGreaterThan(0);
    expect(bodyWeight(clip, 0.15)).toBeLessThan(1);
    expect(bodyWeight(clipWith(), 0.8)).toBe(0);
  });
});

describe("parseClip with landmarks", () => {
  it("keeps valid landmarks", () => {
    expect(parseClip(JSON.parse(JSON.stringify(clipWith(landmarks())))).landmarks?.t).toHaveLength(XS.length);
  });
  it("drops unusable landmarks instead of failing the clip", () => {
    const bad = JSON.parse(JSON.stringify(clipWith(landmarks())));
    bad.landmarks.right[0] = [[1, 2, 3]]; // not 21 points
    expect(parseClip(bad).landmarks).toBeUndefined();
    const badVersion = JSON.parse(JSON.stringify(clipWith(landmarks())));
    badVersion.landmarks.version = 9;
    expect(parseClip(badVersion).landmarks).toBeUndefined();
    const short = JSON.parse(JSON.stringify(clipWith(landmarks())));
    short.landmarks.pose.pop();
    expect(parseClip(short).landmarks).toBeUndefined();
  });
});
