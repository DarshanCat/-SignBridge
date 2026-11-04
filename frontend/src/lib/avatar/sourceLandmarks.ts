import { Vector3 } from "three";
import type { ClipLandmarks } from "./clip";

/** MediaPipe pose indices that the clip landmarks keep. */
export const POSE = { nose: 0, eyeL: 2, eyeR: 5, mouthL: 9, mouthR: 10, shoulderL: 11, shoulderR: 12, elbowL: 13, elbowR: 14, wristL: 15, wristR: 16 } as const;
export type Side = "l" | "r";
export const SIDES: readonly Side[] = ["l", "r"];

/** MediaPipe hand indices: wrist 0, then four points per finger from the knuckle to the tip. */
export const FINGERS = ["thumb", "index", "middle", "ring", "pinky"] as const;
export type Finger = (typeof FINGERS)[number];
export const FINGER_POINTS: Record<Finger, [number, number, number, number]> = {
  thumb: [1, 2, 3, 4], // CMC, MCP, IP, tip
  index: [5, 6, 7, 8], // MCP, PIP, DIP, tip
  middle: [9, 10, 11, 12],
  ring: [13, 14, 15, 16],
  pinky: [17, 18, 19, 20],
};

/** One source frame in rig axes (x toward the signer's left, y up, z toward the camera), units of the signer's shoulder width, origin at the shoulder midpoint. */
export interface SourceFrame {
  nose: Vector3;
  eyes: Vector3;
  mouth: Vector3;
  shoulder: Record<Side, Vector3>;
  elbow: Record<Side, Vector3>;
  wrist: Record<Side, Vector3>;
  /** 21 hand points or null when the hand was not detected at this time. */
  hand: Record<Side, Vector3[] | null>;
}

/**
 * The stored features are normalized by the picture width for x and by the picture height for y, and INCLUDE videos are 16:9, so every vertical
 * distance in them is 16/9 times too long next to a horizontal one. Measured on the data: a signer's upper arm is 1.6 shoulder widths long
 * vertically in the raw numbers but 0.96 after this correction, against 1.01 for the avatar's (the same picture aspect problem as in the paper,
 * here inside the retarget). Directions taken from the raw numbers tilt every limb toward the vertical, so the source is corrected before use.
 */
export const SOURCE_ASPECT_Y = 9 / 16;

/** MediaPipe image space (x right, y down, z depth, nearer is smaller) to rig axes, with the aspect correction. */
const toRig = (p: number[]): Vector3 => new Vector3(p[0], -p[1] * SOURCE_ASPECT_Y, -p[2]);
const lerpV = (a: Vector3, b: Vector3, f: number): Vector3 => a.clone().lerp(b, f);

/**
 * The hand model reports its own depth (z relative to its wrist), so the hand points are used as offsets from the hand's wrist and placed at the
 * pose model's wrist, which is the position the arm reaches.
 */
function handPoints(hand: number[][] | null, poseWrist: Vector3): Vector3[] | null {
  if (!hand) return null;
  const w = toRig(hand[0]);
  return hand.map((p) => toRig(p).sub(w).add(poseWrist));
}

function frameAt(lm: ClipLandmarks, i: number): SourceFrame {
  const at = (idx: number): Vector3 => {
    const k = lm.pose_idx.indexOf(idx);
    if (k < 0) throw new Error(`landmark ${idx} was not stored`);
    return toRig(lm.pose[i][k]);
  };
  const mouth = at(POSE.mouthL).add(at(POSE.mouthR)).multiplyScalar(0.5);
  return {
    nose: at(POSE.nose),
    eyes: at(POSE.eyeL).add(at(POSE.eyeR)).multiplyScalar(0.5),
    mouth,
    shoulder: { l: at(POSE.shoulderL), r: at(POSE.shoulderR) },
    elbow: { l: at(POSE.elbowL), r: at(POSE.elbowR) },
    wrist: { l: at(POSE.wristL), r: at(POSE.wristR) },
    hand: { l: handPoints(lm.left[i], at(POSE.wristL)), r: handPoints(lm.right[i], at(POSE.wristR)) },
  };
}

/** Number of stored source frames. */
export const frameCount = (lm: ClipLandmarks): number => lm.t.length;
export const sourceFrame = (lm: ClipLandmarks, i: number): SourceFrame => frameAt(lm, i);

/** Source frame at clip time t, interpolated between the two neighbouring stored frames (clamped at the ends). A hand counts as present only if it is in both. */
export function sourceFrameAtTime(lm: ClipLandmarks, t: number): SourceFrame {
  const n = lm.t.length;
  if (t <= lm.t[0]) return frameAt(lm, 0);
  if (t >= lm.t[n - 1]) return frameAt(lm, n - 1);
  let i = 0;
  while (i < n - 2 && lm.t[i + 1] <= t) i++;
  const f = (t - lm.t[i]) / (lm.t[i + 1] - lm.t[i] || 1);
  const a = frameAt(lm, i);
  const b = frameAt(lm, i + 1);
  const mix = (x: Record<Side, Vector3>, y: Record<Side, Vector3>): Record<Side, Vector3> => ({ l: lerpV(x.l, y.l, f), r: lerpV(x.r, y.r, f) });
  const hand = (s: Side): Vector3[] | null => (a.hand[s] && b.hand[s] ? a.hand[s]!.map((p, k) => lerpV(p, b.hand[s]![k], f)) : null);
  return {
    nose: lerpV(a.nose, b.nose, f),
    eyes: lerpV(a.eyes, b.eyes, f),
    mouth: lerpV(a.mouth, b.mouth, f),
    shoulder: mix(a.shoulder, b.shoulder),
    elbow: mix(a.elbow, b.elbow),
    wrist: mix(a.wrist, b.wrist),
    hand: { l: hand("l"), r: hand("r") },
  };
}
