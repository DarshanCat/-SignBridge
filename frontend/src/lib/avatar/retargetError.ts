import { Vector3, type Object3D } from "three";
import type { Anatomy } from "./anatomy";
import { FINGER_POINTS, FINGERS, SIDES, type Finger, type Side, type SourceFrame } from "./sourceLandmarks";
import type { HumanoidLike } from "./vrmRig";

/**
 * How far the avatar's pose is from the source landmarks, in two ways that matter for a sign:
 *   position error: where a joint ends up, in units of the shoulder width of EACH body (the source in its own, the avatar in its own), measured
 *     from the shoulder midpoint, so it includes the effect of different arm lengths and body proportions;
 *   direction error: the angle between a bone of the avatar and the same segment of the source, which is about the shape of the arm and hand
 *     and does not depend on proportions.
 * Both are computed from the avatar's real skeleton after a pose has been applied (forward kinematics), not from the numbers fed in.
 */

const VRM_FINGER: Record<Finger, [string, string, string]> = {
  thumb: ["ThumbMetacarpal", "ThumbProximal", "ThumbDistal"],
  index: ["IndexProximal", "IndexIntermediate", "IndexDistal"],
  middle: ["MiddleProximal", "MiddleIntermediate", "MiddleDistal"],
  ring: ["RingProximal", "RingIntermediate", "RingDistal"],
  pinky: ["LittleProximal", "LittleIntermediate", "LittleDistal"],
};
export const JOINT_LABELS: Record<Finger, [string, string, string, string]> = {
  thumb: ["CMC", "MCP", "IP", "tip"],
  index: ["MCP", "PIP", "DIP", "tip"],
  middle: ["MCP", "PIP", "DIP", "tip"],
  ring: ["MCP", "PIP", "DIP", "tip"],
  pinky: ["MCP", "PIP", "DIP", "tip"],
};
const SIDE_NAME: Record<Side, string> = { l: "left", r: "right" };

const bone = (h: HumanoidLike, name: string): Vector3 => (h.getNormalizedBoneNode(name) as Object3D).getWorldPosition(new Vector3());

/** Avatar joint positions of one hand: [base, mid, distal, tip] per finger (the tip extends the last segment, a VRM has no tip bone). */
export function avatarFinger(h: HumanoidLike, side: Side, finger: Finger): [Vector3, Vector3, Vector3, Vector3] {
  const [a, b, c] = VRM_FINGER[finger].map((n) => bone(h, SIDE_NAME[side] + n));
  return [a, b, c, c.clone().add(c.clone().sub(b).multiplyScalar(0.9))];
}

export interface Measurement {
  /** Position error per joint name (e.g. "wrist", "index.tip") in shoulder widths, in 3D. */
  position: Record<string, number>;
  /**
   * The same in the picture plane only (x and y, no depth). The depth of the source is the least reliable part of its landmarks, so this is the
   * error that can be trusted; the 3D error is reported next to it.
   */
  position2d: Record<string, number>;
  /** Direction error per segment name (e.g. "forearm", "index.PIP-DIP") in degrees. */
  direction: Record<string, number>;
  /** Wrist and index tip to mouth: the difference of the vectors from the mouth, in shoulder widths; present only when the hand is near the face. */
  face: Record<string, number>;
}

const angleDeg = (a: Vector3, b: Vector3): number => (Math.acos(Math.min(1, Math.max(-1, a.clone().normalize().dot(b.clone().normalize())))) * 180) / Math.PI;

/** Compare the avatar's current pose with one source frame, for both sides (a hand that the source does not have is skipped). */
export function measureFrame(anat: Anatomy, h: HumanoidLike, src: SourceFrame): Array<{ side: Side; m: Measurement }> {
  const out: Array<{ side: Side; m: Measurement }> = [];
  const av = (p: Vector3): Vector3 => p.clone().sub(anat.shoulderMid).multiplyScalar(1 / anat.sw);
  const mouthAv = av(anat.mouth);
  for (const side of SIDES) {
    const sn = SIDE_NAME[side];
    const hand = src.hand[side];
    if (!hand) continue;
    const m: Measurement = { position: {}, position2d: {}, direction: {}, face: {} };
    const flat = (v: Vector3) => new Vector3(v.x, v.y, 0);
    const shoulderA = bone(h, `${sn}UpperArm`);
    const elbowA = bone(h, `${sn}LowerArm`);
    const wristA = bone(h, `${sn}Hand`);
    m.position.elbow = av(elbowA).distanceTo(src.elbow[side]);
    m.position.wrist = av(wristA).distanceTo(hand[0]);
    m.position2d.elbow = flat(av(elbowA)).distanceTo(flat(src.elbow[side]));
    m.position2d.wrist = flat(av(wristA)).distanceTo(flat(hand[0]));
    m.direction.upperArm = angleDeg(elbowA.clone().sub(shoulderA), src.elbow[side].clone().sub(src.shoulder[side]));
    m.direction.foreArm = angleDeg(wristA.clone().sub(elbowA), hand[0].clone().sub(src.elbow[side]));
    const middleA = avatarFinger(h, side, "middle")[0];
    m.direction.hand = angleDeg(middleA.clone().sub(wristA), hand[9].clone().sub(hand[0]));
    for (const f of FINGERS) {
      const a = avatarFinger(h, side, f);
      const s = FINGER_POINTS[f].map((i) => hand[i]);
      const labels = JOINT_LABELS[f];
      for (let k = 0; k < 4; k++) {
        m.position[`${f}.${labels[k]}`] = av(a[k]).distanceTo(s[k]);
        m.position2d[`${f}.${labels[k]}`] = flat(av(a[k])).distanceTo(flat(s[k]));
      }
      for (let k = 0; k < 2; k++) m.direction[`${f}.${labels[k]}-${labels[k + 1]}`] = angleDeg(a[k + 1].clone().sub(a[k]), s[k + 1].clone().sub(s[k]));
    }
    // near the face: does the hand land at the same place relative to the mouth?
    if (hand[0].distanceTo(src.mouth) < 1.3 || hand[8].distanceTo(src.mouth) < 1.3) {
      const tipA = avatarFinger(h, side, "index")[3];
      m.face.wrist = av(wristA).sub(mouthAv).distanceTo(hand[0].clone().sub(src.mouth));
      m.face.indexTip = av(tipA).sub(mouthAv).distanceTo(hand[8].clone().sub(src.mouth));
    }
    out.push({ side, m });
  }
  return out;
}

export interface Stat {
  n: number;
  mean: number;
  p90: number;
  max: number;
}

export function stat(values: number[]): Stat {
  if (!values.length) return { n: 0, mean: NaN, p90: NaN, max: NaN };
  const s = [...values].sort((a, b) => a - b);
  return { n: s.length, mean: s.reduce((a, b) => a + b, 0) / s.length, p90: s[Math.min(s.length - 1, Math.floor(0.9 * s.length))], max: s[s.length - 1] };
}

/** Collect measurements into per-name value lists, then into statistics. */
export class Accumulator {
  position = new Map<string, number[]>();
  position2d = new Map<string, number[]>();
  /** Per frame and hand: 1 if any point of the hand (wrist, palm, two fingertips) is inside the head or the torso, else 0. */
  penetration = new Map<string, number[]>();
  direction = new Map<string, number[]>();
  face = new Map<string, number[]>();
  addPenetration(hit: "head" | "torso" | null): void {
    for (const [k, v] of [["any", hit ? 1 : 0], ["head", hit === "head" ? 1 : 0], ["torso", hit === "torso" ? 1 : 0]] as const) (this.penetration.get(k) ?? this.penetration.set(k, []).get(k)!).push(v);
  }
  add(m: Measurement): void {
    for (const [k, v] of Object.entries(m.position)) (this.position.get(k) ?? this.position.set(k, []).get(k)!).push(v);
    for (const [k, v] of Object.entries(m.position2d)) (this.position2d.get(k) ?? this.position2d.set(k, []).get(k)!).push(v);
    for (const [k, v] of Object.entries(m.direction)) (this.direction.get(k) ?? this.direction.set(k, []).get(k)!).push(v);
    for (const [k, v] of Object.entries(m.face)) (this.face.get(k) ?? this.face.set(k, []).get(k)!).push(v);
  }
  result() {
    const f = (m: Map<string, number[]>) => Object.fromEntries([...m].map(([k, v]) => [k, stat(v)]));
    return { position: f(this.position), position2d: f(this.position2d), direction: f(this.direction), face: f(this.face), penetration: f(this.penetration) };
  }
}

/** True if a world point is inside the head sphere or the torso (the avatar's own colliders, without any margin). */
export function inBody(anat: Anatomy, p: Vector3): "head" | "torso" | null {
  if (p.distanceTo(anat.head.center) < anat.head.radius * 0.92) return "head";
  const t = anat.torso;
  if (p.y > t.yMin && p.y < t.yMax && Math.hypot((p.x - t.center.x) / t.ax, (p.z - t.center.z) / t.az) < 1) return "torso";
  return null;
}

/** Per hand: does any of wrist, palm centre, index tip, middle tip pass into the head or the torso? */
export function handPenetrates(anat: Anatomy, h: HumanoidLike, side: Side): "head" | "torso" | null {
  const wrist = bone(h, `${SIDE_NAME[side]}Hand`);
  const index = avatarFinger(h, side, "index");
  const middle = avatarFinger(h, side, "middle");
  const palm = wrist.clone().add(middle[0]).multiplyScalar(0.5);
  for (const p of [wrist, palm, index[3], middle[3]]) {
    const hit = inBody(anat, p);
    if (hit) return hit;
  }
  return null;
}
