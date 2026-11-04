import { Euler, Matrix4, Quaternion, Vector3 } from "three";
import type { Anatomy } from "./anatomy";
import type { Euler3, Pose } from "./clip";
import { applyMixamoPose, type MixamoRig } from "./mixamo";
import { FINGER_POINTS, FINGERS, SIDES, type Finger, type Side, type SourceFrame } from "./sourceLandmarks";

/**
 * Retarget one source frame (landmarks of a dataset sample) onto THIS avatar, using its own measurements.
 *
 * What the clip tracks alone cannot give, and what is done here instead:
 *  - the picture aspect of the source is corrected first (see SOURCE_ASPECT_Y), which removes a tilt of every limb toward the vertical;
 *  - hand positions are mapped relative to the avatar's own shoulders and mouth, so a sign at the chin lands at the avatar's chin even though its
 *    head, neck and arms have other proportions than the signer's; a hand cannot pass through the head or the torso;
 *  - the arm is solved with two-bone IK to that place, the elbow hinges only in its anatomical direction (the upper arm rolls to keep it so);
 *  - the hand takes its FULL orientation from the palm (so the wrist and forearm twist is recovered; the VRM's roll bones share it with the forearm);
 *  - every finger joint takes the direction of the source segment, which brings finger spread and thumb opposition that a single curl angle cannot;
 *  - joints are limited to what a hand can do, so a noisy landmark cannot bend a finger backwards or break a wrist.
 * All outputs are rotations in the same canonical frame as the clip tracks, so the rest of the avatar pipeline is unchanged.
 */

export const LIMITS = {
  elbowMax: 2.6, // rad, flexion
  wristSwingMax: 1.35, // rad, angle between the forearm and the hand
  fingerBase: { flex: [-0.35, 1.75] as const, spread: 0.55 }, // rad, knuckle
  fingerMid: [-0.15, 1.9] as const, // rad, PIP
  fingerTip: [-0.1, 1.5] as const, // rad, DIP
  thumbSwing: 1.5, // rad, per thumb joint
  reach: 0.985, // share of the arm length that may be used
  /** Clearance kept between the wrist and the torso or head, in avatar shoulder widths (so a hand stays clear of the clothes and the hair). */
  torsoMargin: 0.1,
  headMargin: 0.0,
} as const;

const DOWN = new Vector3(0, -1, 0);
const clamp = (x: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, x));
const smooth = (x: number) => {
  const c = clamp(x, 0, 1);
  return c * c * (3 - 2 * c);
};
const toEuler = (q: Quaternion): Euler3 => {
  const e = new Euler().setFromQuaternion(q, "XYZ");
  return [e.x, e.y, e.z];
};

function basis(f: Vector3, u: Vector3): Matrix4 {
  const y = f.clone().normalize();
  const x = u.clone().sub(y.clone().multiplyScalar(u.dot(y))).normalize();
  const z = new Vector3().crossVectors(x, y);
  return new Matrix4().makeBasis(x, y, z);
}

/** Rotation taking the frame (forward fa, side ua) to the frame (fb, ub); u is orthogonalised against f. */
export function frameRotation(fa: Vector3, ua: Vector3, fb: Vector3, ub: Vector3): Quaternion {
  const m = basis(fb, ub).multiply(basis(fa, ua).transpose());
  return new Quaternion().setFromRotationMatrix(m);
}

/** Split q into a swing (bend) and a twist about the given axis: q = swing * twist. */
function swingTwist(q: Quaternion, axis: Vector3): { swing: Quaternion; twist: Quaternion } {
  const r = new Vector3(q.x, q.y, q.z);
  const p = axis.clone().multiplyScalar(r.dot(axis));
  const twist = new Quaternion(p.x, p.y, p.z, q.w);
  if (twist.lengthSq() < 1e-12) twist.set(0, 0, 0, 1);
  twist.normalize();
  return { swing: q.clone().multiply(twist.clone().invert()), twist };
}

/** Limit the angle of a rotation (shortest arc) to max by moving it toward the identity. */
function limitAngle(q: Quaternion, max: number): Quaternion {
  const angle = 2 * Math.acos(clamp(Math.abs(q.w), 0, 1));
  return angle <= max ? q : new Quaternion().slerp(q, max / angle);
}

export interface Solved {
  pose: Pose;
  /** Which sides were solved from the source (arm) and which of those also got the hand and fingers. */
  arm: Record<Side, boolean>;
  hand: Record<Side, boolean>;
  /** Where the solved wrists are, for checks and the overlay. */
  wrist: Record<Side, Vector3 | null>;
}

interface FingerRest {
  /** Canonical rest direction of each of the three joint bones (to the next joint; the last one repeats the previous). */
  dir: [Vector3, Vector3, Vector3];
}

interface SideRest {
  shoulder: Vector3;
  upperDir: Vector3; // upper arm rest direction (world)
  foreDir: Vector3;
  handF: Vector3; // hand rest frame: toward the middle knuckle and across the knuckles (index to pinky)
  handU: Vector3;
  fingers: Record<Finger, FingerRest>;
}

export class SignRetargeter {
  private rest: Record<Side, SideRest>;
  private upperLen: Record<Side, number>;
  private foreLen: Record<Side, number>;
  readonly options = { mapToBody: true, collide: true, liftDepth: true };

  constructor(
    private rig: MixamoRig,
    private anat: Anatomy,
  ) {
    applyMixamoPose(rig, {});
    this.rest = { l: this.measureSide("l"), r: this.measureSide("r") };
    this.upperLen = { l: anat.armLen.l[0], r: anat.armLen.r[0] };
    this.foreLen = { l: anat.armLen.l[1], r: anat.armLen.r[1] };
  }

  private bone(clip: string): Vector3 {
    const j = this.rig.joints.find((x) => x.clipBone === clip);
    if (!j) throw new Error(`rig has no joint ${clip}`);
    return j.bone.getWorldPosition(new Vector3());
  }

  private measureSide(s: Side): SideRest {
    const shoulder = this.bone(`upperArm_${s}`);
    const elbow = this.bone(`foreArm_${s}`);
    const hand = this.bone(`hand_${s}`);
    const fingers = {} as Record<Finger, FingerRest>;
    const base: Record<string, Vector3> = {};
    for (const f of FINGERS) {
      const p = [1, 2, 3].map((k) => this.bone(`hand_${s}.${f}#${k}`));
      base[f] = p[0];
      const d1 = p[1].clone().sub(p[0]).normalize();
      const d2 = p[2].clone().sub(p[1]).normalize();
      fingers[f] = { dir: [d1, d2, d2.clone()] };
    }
    return {
      shoulder,
      upperDir: elbow.clone().sub(shoulder).normalize(),
      foreDir: hand.clone().sub(elbow).normalize(),
      handF: base.middle.clone().sub(hand).normalize(),
      handU: base.pinky.clone().sub(base.index).normalize(),
      fingers,
    };
  }

  /** Source point (rig axes, shoulder widths from the signer's shoulder midpoint) to avatar world space, anchored at the mouth. */
  mapPoint(p: Vector3, src: SourceFrame): Vector3 {
    const a = this.anat;
    const base = a.shoulderMid.clone().add(p.clone().multiplyScalar(a.sw));
    if (!this.options.mapToBody) return base;
    const mouthBase = a.shoulderMid.clone().add(src.mouth.clone().multiplyScalar(a.sw));
    const offset = a.mouth.clone().sub(mouthBase);
    // the correction grows from nothing at the shoulders to the full offset at the mouth and stays above it
    const m = Math.max(src.mouth.y, 0.2);
    const w = smooth((p.y - 0.25 * m) / (0.75 * m));
    return base.add(offset.multiplyScalar(w));
  }

  /**
   * The depth of a pose landmark is the least reliable number the source has (arms come out far longer than arms can be). The picture-plane
   * position of each joint is trusted, and the depth is rebuilt from the bone length: dz = +-sqrt(length^2 - dx^2 - dy^2), with the sign of the
   * source depth. Lengths are this avatar's own. A limb that the picture shows longer than the bone gets no depth.
   */
  private liftArm(src: SourceFrame, s: Side): { elbow: Vector3; wrist: Vector3 } {
    if (!this.options.liftDepth) return { elbow: src.elbow[s], wrist: src.wrist[s] };
    const unit = this.anat.sw;
    const limb = (from: Vector3, to: Vector3, len: number): Vector3 => {
      const v = to.clone().sub(from);
      const rho = Math.hypot(v.x, v.y);
      if (rho >= len) return from.clone().add(new Vector3(v.x * (len / rho), v.y * (len / rho), 0));
      const sign = Math.abs(v.z) < 0.05 ? 1 : Math.sign(v.z); // with no depth cue, forward (toward the viewer) is the usual way an arm points
      return from.clone().add(new Vector3(v.x, v.y, sign * Math.sqrt(len * len - rho * rho)));
    };
    const elbow = limb(src.shoulder[s], src.elbow[s], this.upperLen[s] / unit);
    return { elbow, wrist: limb(elbow, src.wrist[s], this.foreLen[s] / unit) };
  }

  /** Push a wrist target out of the head and the torso (touching is allowed, passing through is not). */
  private collide(p: Vector3): Vector3 {
    if (!this.options.collide) return p;
    const a = this.anat;
    const out = p.clone();
    const head = a.head;
    const r = head.radius * 0.92 + LIMITS.headMargin * a.sw;
    const dh = out.clone().sub(head.center);
    if (dh.length() < r && dh.length() > 1e-6) out.copy(head.center).add(dh.setLength(r));
    const t = a.torso;
    if (out.y > t.yMin && out.y < t.yMax) {
      const ax = t.ax + LIMITS.torsoMargin * a.sw;
      const az = t.az + LIMITS.torsoMargin * a.sw;
      const dx = (out.x - t.center.x) / ax;
      const dz = (out.z - t.center.z) / az;
      const k = Math.hypot(dx, dz);
      if (k < 1) {
        // out through the front unless the point is clearly behind the body
        const front = dz >= -0.2 ? 1 : -1;
        const nz = front * Math.sqrt(Math.max(0, 1 - dx * dx));
        out.z = t.center.z + nz * az;
        if (Math.abs(nz) < 0.05) out.x = t.center.x + Math.sign(dx || 1) * ax;
      }
    }
    return out;
  }

  /** Solve one source frame. The result only contains the bones it solved; the caller keeps the clip's own pose for the rest. */
  solve(src: SourceFrame): Solved {
    const pose: Pose = {};
    const res: Solved = { pose, arm: { l: false, r: false }, hand: { l: false, r: false }, wrist: { l: null, r: null } };
    for (const s of SIDES) {
      const sh = this.anat.shoulder[s];
      const L1 = this.upperLen[s];
      const L2 = this.foreLen[s];
      const hand = src.hand[s];
      const lifted = this.liftArm(src, s);
      let wTarget = this.collide(this.mapPoint(lifted.wrist, src));
      let reach = wTarget.clone().sub(sh);
      const maxReach = (L1 + L2) * LIMITS.reach;
      const minReach = Math.abs(L1 - L2) + 0.02 * this.anat.sw;
      if (reach.length() > maxReach) reach.setLength(maxReach);
      if (reach.length() < minReach) reach.setLength(minReach);
      wTarget = sh.clone().add(reach);
      const d = reach.length();
      const u = reach.clone().divideScalar(d);

      // elbow: on the circle of two-bone solutions, toward where the source elbow is
      const elbowSrc = this.mapPoint(lifted.elbow, src).sub(sh);
      let pole = elbowSrc.clone().sub(u.clone().multiplyScalar(elbowSrc.dot(u)));
      if (pole.length() < 1e-4) {
        const raw = new Vector3(0, -0.3, -1); // an elbow hangs back and down when nothing says otherwise
        pole = raw.sub(u.clone().multiplyScalar(raw.dot(u)));
      }
      pole.normalize();
      const a = (L1 * L1 - L2 * L2 + d * d) / (2 * d);
      const hgt = Math.sqrt(Math.max(0, L1 * L1 - a * a));
      const elbow = sh.clone().add(u.clone().multiplyScalar(a)).add(pole.clone().multiplyScalar(hgt));
      const dUpper = elbow.clone().sub(sh).normalize();
      const dFore = wTarget.clone().sub(elbow).normalize();

      // upper arm: its hinge axis (rest: x) goes to the normal of the arm plane, so the elbow only bends the way an elbow can
      const flex = clamp(Math.acos(clamp(dUpper.dot(dFore), -1, 1)), 0, LIMITS.elbowMax);
      const hinge = new Vector3().crossVectors(dUpper, dFore);
      let wUpper: Quaternion;
      if (hinge.length() < 0.05) wUpper = new Quaternion().setFromUnitVectors(DOWN, dUpper);
      else {
        hinge.normalize();
        // rest: bending the forearm forward (+z) about -x, so the plane normal cross(down, forward) is -x
        wUpper = frameRotation(DOWN, new Vector3(-1, 0, 0), dUpper, hinge);
      }
      const wFore = wUpper.clone().multiply(new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), -flex));
      pose[`upperArm_${s}`] = toEuler(wUpper);
      pose[`foreArm_${s}`] = toEuler(wUpper.clone().invert().multiply(wFore));
      res.arm[s] = true;
      res.wrist[s] = wTarget;

      if (!hand) continue;
      // hand: full orientation from the palm (forward to the middle knuckle, across the knuckles from index to pinky)
      const rest = this.rest[s];
      const fObs = hand[9].clone().sub(hand[0]);
      const uObs = hand[17].clone().sub(hand[5]);
      const wWanted = frameRotation(rest.handF, rest.handU, fObs, uObs);
      // the wrist bends only so far; the twist about the forearm is free (the VRM's roll bones share it with the forearm)
      const { swing, twist } = swingTwist(wFore.clone().invert().multiply(wWanted), DOWN);
      const localHand = limitAngle(swing, LIMITS.wristSwingMax).multiply(twist);
      const wHand = wFore.clone().multiply(localHand);
      pose[`hand_${s}`] = toEuler(localHand);

      // fingers: each joint takes the direction of the source segment
      for (const f of FINGERS) {
        const idx = FINGER_POINTS[f];
        const pts = idx.map((i) => hand[i]);
        let wParent = wHand.clone();
        for (let k = 0; k < 3; k++) {
          const want = pts[k + 1].clone().sub(pts[k]).normalize();
          const dLocal = want.applyQuaternion(wParent.clone().invert());
          const restDir = rest.fingers[f].dir[k];
          let q = new Quaternion().setFromUnitVectors(restDir, dLocal);
          q = this.limitFinger(f, k, q, restDir);
          pose[`hand_${s}.${f}#${k + 1}`] = toEuler(q);
          wParent = wParent.clone().multiply(q);
        }
      }
      res.hand[s] = true;
    }
    return res;
  }

  /** Keep a finger joint to what it can do: knuckles flex and spread, the other joints only flex, the thumb swings within a cone. */
  private limitFinger(f: Finger, k: number, q: Quaternion, restDir: Vector3): Quaternion {
    if (f === "thumb") return limitAngle(q, LIMITS.thumbSwing);
    // flexion about the finger's own lateral axis (canonical x), spread about the palm normal (canonical z)
    const d = restDir.clone().applyQuaternion(q);
    const flexion = -Math.atan2(d.z, -d.y) - -Math.atan2(restDir.z, -restDir.y);
    const spread = Math.atan2(d.x, -d.y) - Math.atan2(restDir.x, -restDir.y);
    const [lo, hi] = k === 0 ? LIMITS.fingerBase.flex : k === 1 ? LIMITS.fingerMid : LIMITS.fingerTip;
    const fl = clamp(-flexion, lo, hi); // positive = curled toward the palm
    const sp = k === 0 ? clamp(spread, -LIMITS.fingerBase.spread, LIMITS.fingerBase.spread) : 0;
    // rebuild: spread (about z) after flexion (about x), applied to the rest direction frame
    return new Quaternion().setFromEuler(new Euler(-fl, 0, sp, "XYZ"));
  }
}

/** Overlay a solved frame onto the clip's own pose: solved bones replace the clip's, everything else is kept. */
export function mergePose(clipPose: Pose, solved: Solved): Pose {
  const out: Pose = { ...clipPose };
  for (const s of SIDES) {
    if (solved.hand[s]) {
      // the finger joints of this hand come from the solve, so the clip's single curl angle must not be applied on top
      for (const f of FINGERS) delete out[`hand_${s}.${f}`];
    }
  }
  return Object.assign(out, solved.pose);
}
