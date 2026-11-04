import { Euler, Quaternion } from "three";
import type { Euler3, Pose } from "./clip";

/**
 * Presentation layer that sits between the sequence player and the skeleton. It never edits a clip: it only
 *  - adds a very small breathing, weight shift and head drift to the torso (always),
 *  - relaxes an arm that is hanging at rest (slight outward angle and elbow bend, softly curled and slightly fanned fingers) and fades that
 *    out completely as soon as the arm is lifted, so a sign is played exactly as it was retargeted,
 *  - smooths the final pose so nothing snaps (start of a sentence, between clips, end of a sentence).
 */

export const IDLE = {
  breathHz: 0.22,
  breathChest: 0.014, // rad
  breathSpine: 0.008,
  swayHz: 0.065,
  swaySpine: 0.022,
  driftHz: 0.045,
  driftHead: 0.035,
  armOut: 0.07, // upper arm angled away from the body
  elbowBend: 0.2, // fore arm bent forward
  restFades: [0.1, 0.45] as const, // arm lift (rad, upper arm plus fore arm) over which the relaxed offsets fade out
} as const;

/** Total finger curl (rad, negative closes the hand) of a relaxed hand; thumb is straighter than the little finger. */
const REST_CURL: Record<string, number> = { thumb: -0.1, index: -0.25, middle: -0.32, ring: -0.4, pinky: -0.48 };
/** Sideways fan of the finger at its first joint for the left hand (right hand mirrored). The thumb is not fanned. */
const REST_FAN: Record<string, number> = { index: 0.08, middle: 0.0, ring: -0.06, pinky: -0.12 };

export type Spread = Record<string, number>;

export const smoothstep = (x: number): number => {
  const c = Math.min(1, Math.max(0, x));
  return c * c * (3 - 2 * c);
};

const norm = (e: Euler3 | undefined): number => (e ? Math.hypot(e[0], e[1], e[2]) : 0);

/** 1 while the arm hangs at rest, 0 once it is lifted for a sign. */
export function restWeight(pose: Pose, side: "l" | "r"): number {
  const lift = norm(pose[`upperArm_${side}`]) + norm(pose[`foreArm_${side}`]);
  return 1 - smoothstep((lift - IDLE.restFades[0]) / (IDLE.restFades[1] - IDLE.restFades[0]));
}

/**
 * Pose plus the relaxed rest layer at time t (seconds). Always returns all 20 bones.
 * calm: the visitor asked for reduced motion, so the decorative idle movement (breathing, weight shift, head drift) is switched off; the
 * relaxed hands stay, because they are a pose and not a movement.
 */
export function withRelaxedRest(pose: Pose, t: number, calm = false): { pose: Pose; spread: Spread } {
  const out: Pose = {};
  const spread: Spread = {};
  const get = (b: string): Euler3 => pose[b] ?? [0, 0, 0];
  const add = (b: string, dx: number, dy = 0, dz = 0) => {
    const e = out[b] ?? get(b);
    out[b] = [e[0] + dx, e[1] + dy, e[2] + dz];
  };
  const k = calm ? 0 : 1;
  const breath = k * Math.sin(2 * Math.PI * IDLE.breathHz * t);
  const sway = k * Math.sin(2 * Math.PI * IDLE.swayHz * t);
  const drift = k * Math.sin(2 * Math.PI * IDLE.driftHz * t + 1.3);
  const nod = k * Math.sin(2 * Math.PI * IDLE.driftHz * 0.7 * t);
  add("spine", IDLE.breathSpine * breath, 0, IDLE.swaySpine * sway);
  add("chest", IDLE.breathChest * breath, 0, -IDLE.swaySpine * 0.5 * sway);
  add("neck", -IDLE.breathSpine * 0.5 * breath, 0, IDLE.swaySpine * 0.25 * sway);
  add("head", IDLE.driftHead * 0.3 * nod, IDLE.driftHead * drift, -IDLE.swaySpine * 0.4 * sway);

  for (const side of ["l", "r"] as const) {
    const w = restWeight(pose, side);
    const sign = side === "l" ? 1 : -1;
    add(`upperArm_${side}`, 0, 0, sign * IDLE.armOut * w);
    add(`foreArm_${side}`, -IDLE.elbowBend * w);
    add(`hand_${side}`, 0, 0, 0);
    for (const [finger, curl] of Object.entries(REST_CURL)) {
      add(`hand_${side}.${finger}`, curl * w);
      if (finger in REST_FAN) spread[`hand_${side}.${finger}`] = sign * REST_FAN[finger] * w;
    }
  }
  return { pose: out, spread };
}

const tmpE = new Euler();
const toQuat = (e: Euler3) => new Quaternion().setFromEuler(tmpE.set(e[0], e[1], e[2], "XYZ"));
const toEuler = (q: Quaternion): Euler3 => {
  tmpE.setFromQuaternion(q, "XYZ");
  return [tmpE.x, tmpE.y, tmpE.z];
};

/** Rotations of one bone interpolated as quaternions (shortest path, constant speed); f in 0..1. */
export function slerpEuler(a: Euler3, b: Euler3, f: number): Euler3 {
  return toEuler(toQuat(a).slerp(toQuat(b), f));
}

/**
 * Frame-rate independent smoothing of the rendered pose toward the target pose. Bones are slerped as quaternions; finger joints
 * (names with a dot) only curl about x, so they are smoothed as plain numbers.
 */
export class PoseSmoother {
  private q = new Map<string, Quaternion>();
  private f = new Map<string, Euler3>();
  private spread: Spread = {};

  /** tau: time constant in seconds (the pose covers 63 percent of the remaining distance in tau). */
  constructor(private tau = 0.07) {}

  /** The time constant can be given per step: short inside a sign (it keeps the handshape crisp), longer between signs. */

  reset(): void {
    this.q.clear();
    this.f.clear();
    this.spread = {};
  }

  step(target: Pose, spread: Spread, dt: number, tau: number = this.tau): { pose: Pose; spread: Spread } {
    const a = dt <= 0 ? 1 : 1 - Math.exp(-dt / tau);
    const pose: Pose = {};
    for (const [bone, e] of Object.entries(target)) {
      if (bone.includes(".")) {
        const prev = this.f.get(bone) ?? e;
        const next: Euler3 = [prev[0] + (e[0] - prev[0]) * a, prev[1] + (e[1] - prev[1]) * a, prev[2] + (e[2] - prev[2]) * a];
        this.f.set(bone, next);
        pose[bone] = next;
      } else {
        const tq = toQuat(e);
        const cur = this.q.get(bone);
        const next = cur ? cur.slerp(tq, a) : tq;
        this.q.set(bone, next);
        pose[bone] = toEuler(next);
      }
    }
    for (const [k, v] of Object.entries(spread)) {
      const prev = this.spread[k] ?? v;
      this.spread[k] = prev + (v - prev) * a;
    }
    return { pose, spread: { ...this.spread } };
  }
}
