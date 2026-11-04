import { Euler, Quaternion, Vector3, type Bone, type Object3D } from "three";
import type { Pose } from "./clip";

/**
 * Drives a Mixamo skeleton (3 joints per finger) with SignBridge clips.
 *
 * Clip rotations are expressed in a canonical frame in which every bone is axis aligned in the rest pose, arms hang down (-y) and the
 * palms face forward (+z). A Mixamo model rests in a T-pose with palms down, so the canonical arms-down pose is DERIVED from the loaded
 * skeleton (arm direction and palm normal measured from its bones), not assumed. For each animated bone:
 *     world rotation = canonical clip rotation (accumulated down the chain) * Qc
 * where Qc is the bone's T-pose world rotation turned into the arms-down pose. The local rotation then follows from the parent's real
 * world rotation. Bones with no clip track therefore sit in the arms-down rest pose, so the avatar stands correctly with no clip.
 */

const FINGERS = ["Thumb", "Index", "Middle", "Ring", "Pinky"] as const;
export const FINGER_SPLIT: Record<string, [number, number, number]> = {
  Thumb: [0.3, 0.4, 0.3],
  Index: [0.4, 0.4, 0.2],
  Middle: [0.4, 0.4, 0.2],
  Ring: [0.4, 0.4, 0.2],
  Pinky: [0.4, 0.4, 0.2],
};
const TORSO: [string, string][] = [["spine", "Spine"], ["chest", "Spine2"], ["neck", "Neck"], ["head", "Head"]];
const REST_DOWN = new Vector3(0, -1, 0);
const FORWARD = new Vector3(0, 0, 1);

export interface Joint {
  clipBone: string; // our clip bone name, e.g. hand_l.index
  bone: Object3D; // a Mixamo Bone or, for a VRM, a normalized humanoid bone node
  qc: Quaternion; // T-pose world rotation turned into the arms-down canonical pose
  fraction: number; // share of the clip rotation (finger curl is split over three joints)
  parentClip: string | null; // canonical parent (clip bone name), null for the canonical root
  rotateX?: boolean; // finger joints only curl about x
}

export interface MixamoRig {
  root: Object3D;
  joints: Joint[]; // parents before children
  boneNames: string[];
}

const norm = (s: string) => s.replace(/[^A-Za-z0-9_]/g, "");

/** three.js removes ":" from node names ("mixamorig:Hips" becomes "mixamorigHips"), so compare with punctuation stripped. */
export function findBone(root: Object3D, suffix: string): Bone | undefined {
  const want = "mixamorig" + suffix;
  let found: Bone | undefined;
  root.traverse((o) => {
    if ((o as Bone).isBone && norm(o.name) === want) found = o as Bone;
  });
  return found;
}

export function requiredMixamoBones(): string[] {
  const names = TORSO.map(([, m]) => m);
  for (const side of ["Left", "Right"]) {
    names.push(`${side}Arm`, `${side}ForeArm`, `${side}Hand`);
    for (const f of FINGERS) for (const k of [1, 2, 3]) names.push(`${side}Hand${f}${k}`);
  }
  return names;
}

export function missingMixamoBones(root: Object3D): string[] {
  return requiredMixamoBones().filter((n) => !findBone(root, n));
}

const worldPos = (b: Object3D) => b.getWorldPosition(new Vector3());
const worldQuat = (b: Object3D) => b.getWorldQuaternion(new Quaternion());

/** The bones that fix the arm direction and the palm normal of one side; any skeleton (Mixamo, VRM) can supply them. */
export interface ArmBones {
  arm: Object3D;
  foreArm: Object3D;
  hand: Object3D;
  indexBase: Object3D;
  middleBase: Object3D;
  pinkyBase: Object3D;
}

/** Rotation that takes the T-pose arm to the arms-down pose with the palm facing forward, measured from the skeleton. */
export function armsDownRotation(root: Object3D, side: "Left" | "Right"): Quaternion {
  const get = (n: string) => findBone(root, `${side}${n}`) as Bone;
  return armsDownFromBones({ arm: get("Arm"), foreArm: get("ForeArm"), hand: get("Hand"), indexBase: get("HandIndex1"), middleBase: get("HandMiddle1"), pinkyBase: get("HandPinky1") });
}

export function armsDownFromBones(b: ArmBones): Quaternion {
  const dir = worldPos(b.foreArm).sub(worldPos(b.arm)).normalize();
  const down = new Quaternion().setFromUnitVectors(dir, REST_DOWN);
  const f = worldPos(b.middleBase).sub(worldPos(b.hand));
  const u = worldPos(b.pinkyBase).sub(worldPos(b.indexBase));
  const n = new Vector3().crossVectors(f, u).normalize();
  if (n.y > 0) n.negate(); // a Mixamo T-pose has the palms facing down
  n.applyQuaternion(down);
  const proj = (v: Vector3) => v.clone().addScaledVector(REST_DOWN, -v.dot(REST_DOWN)).normalize();
  const a = proj(n);
  const t = proj(FORWARD);
  const angle = Math.atan2(REST_DOWN.dot(new Vector3().crossVectors(a, t)), a.dot(t));
  return new Quaternion().setFromAxisAngle(REST_DOWN, angle).multiply(down);
}

export function buildMixamoRig(root: Object3D): MixamoRig {
  const missing = missingMixamoBones(root);
  if (missing.length) throw new Error(`avatar skeleton is missing bones: ${missing.join(", ")}`);
  return buildRigFromLookup(root, (n) => findBone(root, n) as Bone);
}

/**
 * Build the rig from any skeleton. `lookup` returns the bone for a slot named like the Mixamo suffixes ("Spine2", "LeftArm", "LeftHandIndex1");
 * a VRM supplies its normalized humanoid bones through the table in vrmRig.ts. The arms-down rest pose is derived from the bones it returns.
 */
export function buildRigFromLookup(root: Object3D, lookup: (slot: string) => Object3D): MixamoRig {
  root.updateMatrixWorld(true);
  const armBones = (side: "Left" | "Right"): ArmBones => ({
    arm: lookup(`${side}Arm`),
    foreArm: lookup(`${side}ForeArm`),
    hand: lookup(`${side}Hand`),
    indexBase: lookup(`${side}HandIndex1`),
    middleBase: lookup(`${side}HandMiddle1`),
    pinkyBase: lookup(`${side}HandPinky1`),
  });
  const D = { Left: armsDownFromBones(armBones("Left")), Right: armsDownFromBones(armBones("Right")) };
  const joints: Joint[] = [];
  const add = (clipBone: string, mixamo: string, parentClip: string | null, d: Quaternion | null, fraction = 1, rotateX = false) => {
    const bone = lookup(mixamo);
    const qc = (d ? d.clone() : new Quaternion()).multiply(worldQuat(bone));
    joints.push({ clipBone, bone, qc, fraction, parentClip, rotateX });
  };
  let prev: string | null = null;
  for (const [clip, mx] of TORSO) {
    add(clip, mx, prev, null);
    prev = clip;
  }
  for (const [side, key] of [["l", "Left"], ["r", "Right"]] as const) {
    const d = D[key];
    add(`upperArm_${side}`, `${key}Arm`, "chest", d);
    add(`foreArm_${side}`, `${key}ForeArm`, `upperArm_${side}`, d);
    add(`hand_${side}`, `${key}Hand`, `foreArm_${side}`, d);
    for (const f of FINGERS) {
      const clip = `hand_${side}.${f.toLowerCase()}`;
      let parent = `hand_${side}`;
      for (const k of [1, 2, 3]) {
        const name = `${clip}#${k}`;
        add(name, `${key}Hand${f}${k}`, parent, d, FINGER_SPLIT[f][k - 1], true);
        parent = name;
      }
    }
  }
  return { root, joints, boneNames: joints.map((j) => j.bone.name) };
}

const tmpQ = new Quaternion();
const tmpE = new Euler();

/**
 * Apply a clip pose (our 20 bone names) to the skeleton. Missing bones in the pose are at rest.
 * spread (optional, rad, keyed by finger clip bone such as hand_l.index) fans a finger sideways at its first joint; clips never carry it,
 * only the relaxed rest layer does.
 */
export function applyMixamoPose(rig: MixamoRig, pose: Pose, spread: Record<string, number> = {}): void {
  const canon = new Map<string, Quaternion>();
  for (const j of rig.joints) {
    const key = j.clipBone.split("#")[0];
    const direct = pose[j.clipBone]; // a solved pose gives this joint its own full rotation (finger joints: name#1 to name#3)
    const e = pose[key] ?? [0, 0, 0];
    const fan = j.rotateX && j.clipBone.endsWith("#1") ? (spread[key] ?? 0) : 0;
    const r = direct ? tmpE.set(direct[0], direct[1], direct[2], "XYZ") : j.rotateX ? tmpE.set(e[0] * j.fraction, 0, fan, "XYZ") : tmpE.set(e[0], e[1], e[2], "XYZ");
    const local = new Quaternion().setFromEuler(r);
    const parent = j.parentClip ? (canon.get(j.parentClip) ?? new Quaternion()) : new Quaternion();
    const w = parent.clone().multiply(local);
    canon.set(j.clipBone, w);
    const target = w.clone().multiply(j.qc);
    const parentWorld = j.bone.parent ? worldQuat(j.bone.parent) : tmpQ.identity().clone();
    j.bone.quaternion.copy(parentWorld.invert().multiply(target));
    j.bone.updateMatrixWorld(true);
  }
}

/** Direction (world, unit) from a bone to its first child bone: used to check poses. */
export function boneDirection(bone: Object3D): Vector3 {
  const child = bone.children.find((c) => (c as Bone).isBone);
  if (!child) throw new Error(`${bone.name} has no child bone`);
  return worldPos(child).sub(worldPos(bone)).normalize();
}
