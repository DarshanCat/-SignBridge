import { Vector3, type BufferAttribute, type Mesh, type Object3D } from "three";
import { applyMixamoPose, type MixamoRig } from "./mixamo";
import type { Side } from "./sourceLandmarks";
import type { HumanoidLike } from "./vrmRig";

/**
 * Measurements of the loaded avatar that a retarget needs: where its shoulders, mouth and head are and how long its arms are. They are READ from
 * the model (bone positions in the arms-down rest pose and the vertices of its meshes), never assumed, so a different VRM works the same way.
 */
export interface Anatomy {
  shoulder: Record<Side, Vector3>;
  shoulderMid: Vector3;
  /** Distance between the two shoulder joints: the unit in which signs are scaled to this body. */
  sw: number;
  /** Upper arm and forearm length. */
  armLen: Record<Side, [number, number]>;
  mouth: Vector3;
  eyes: Vector3;
  head: { center: Vector3; radius: number };
  /** Upper torso as an elliptic cylinder: centre, half width, half depth, vertical range. */
  torso: { center: Vector3; ax: number; az: number; yMin: number; yMax: number };
  /** Where the mouth came from: the model's own mouth morph target, or an estimate from the eyes. */
  mouthFrom: "morph" | "estimate";
}

const pos = (h: HumanoidLike, name: string): Vector3 => (h.getNormalizedBoneNode(name) as Object3D).getWorldPosition(new Vector3());

function eachVertex(root: Object3D, cb: (p: Vector3, mesh: Mesh) => void): void {
  const p = new Vector3();
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    const mesh = o as Mesh;
    const a = mesh.geometry?.attributes?.position as BufferAttribute | undefined;
    if (!mesh.isMesh || !a) return;
    for (let i = 0; i < a.count; i++) cb(p.fromBufferAttribute(a, i).applyMatrix4(mesh.matrixWorld), mesh);
  });
}

/** Centre of the vertices that the mouth-open morph target moves most: that is where the model's mouth is. */
function mouthFromMorph(root: Object3D): Vector3 | null {
  let found: Vector3 | null = null;
  root.traverse((o) => {
    const mesh = o as Mesh;
    const dict = mesh.morphTargetDictionary;
    const attrs = mesh.geometry?.morphAttributes?.position as BufferAttribute[] | undefined;
    if (!mesh.isMesh || !dict || !attrs || found) return;
    const key = Object.keys(dict).find((k) => /(^|[_.])MTH[_.]?A$/i.test(k) || /Mth_A$/i.test(k));
    if (key === undefined) return;
    const morph = attrs[dict[key]];
    const base = mesh.geometry.attributes.position as BufferAttribute;
    const relative = mesh.geometry.morphTargetsRelative;
    const d: number[] = [];
    let max = 0;
    for (let i = 0; i < base.count; i++) {
      const dx = morph.getX(i) - (relative ? 0 : base.getX(i));
      const dy = morph.getY(i) - (relative ? 0 : base.getY(i));
      const dz = morph.getZ(i) - (relative ? 0 : base.getZ(i));
      const m = Math.hypot(dx, dy, dz);
      d.push(m);
      max = Math.max(max, m);
    }
    if (max <= 0) return;
    const c = new Vector3();
    let w = 0;
    const v = new Vector3();
    for (let i = 0; i < base.count; i++) {
      if (d[i] < 0.4 * max) continue;
      c.add(v.fromBufferAttribute(base, i).applyMatrix4(mesh.matrixWorld).multiplyScalar(d[i]));
      w += d[i];
    }
    if (w > 0) found = c.multiplyScalar(1 / w);
  });
  return found;
}

/** Read the avatar's anatomy. Leaves the rig in the canonical arms-down rest pose. */
export function measureAnatomy(root: Object3D, humanoid: HumanoidLike, rig: MixamoRig): Anatomy {
  applyMixamoPose(rig, {});
  root.updateMatrixWorld(true);
  const shoulder = { l: pos(humanoid, "leftUpperArm"), r: pos(humanoid, "rightUpperArm") };
  const shoulderMid = shoulder.l.clone().add(shoulder.r).multiplyScalar(0.5);
  const sw = shoulder.l.distanceTo(shoulder.r);
  const armLen = {
    l: [shoulder.l.distanceTo(pos(humanoid, "leftLowerArm")), pos(humanoid, "leftLowerArm").distanceTo(pos(humanoid, "leftHand"))] as [number, number],
    r: [shoulder.r.distanceTo(pos(humanoid, "rightLowerArm")), pos(humanoid, "rightLowerArm").distanceTo(pos(humanoid, "rightHand"))] as [number, number],
  };

  const eyeBones = ["leftEye", "rightEye"].map((n) => humanoid.getNormalizedBoneNode(n)).filter((b): b is Object3D => !!b);
  const neck = pos(humanoid, "neck");
  const headBone = pos(humanoid, "head");
  const eyes = eyeBones.length === 2 ? eyeBones[0].getWorldPosition(new Vector3()).add(eyeBones[1].getWorldPosition(new Vector3())).multiplyScalar(0.5) : headBone.clone().add(new Vector3(0, 0.08 * sw, 0.05 * sw));

  // head: the vertices above the neck give its centre and size (hair included, so a hand also keeps off the hair)
  const lo = new Vector3(Infinity, Infinity, Infinity);
  const hi = new Vector3(-Infinity, -Infinity, -Infinity);
  eachVertex(root, (p) => {
    if (p.y < neck.y + 0.05 * sw || Math.abs(p.x) > 0.9 * sw) return; // above the neck, and not the T-pose arms that reach that high
    lo.min(p);
    hi.max(p);
  });
  const hasHead = Number.isFinite(lo.x);
  const size = hasHead ? hi.clone().sub(lo) : new Vector3(sw, sw, sw);
  const head = { center: hasHead ? lo.clone().add(hi).multiplyScalar(0.5) : headBone.clone(), radius: 0.5 * Math.max(size.x, size.y) * 0.82 };

  const m = mouthFromMorph(root);
  const mouth = m ?? eyes.clone().add(new Vector3(0, -0.42 * (eyes.y - neck.y) * 0.5, 0.02 * sw));

  // upper torso: the chest vertices near the midline give its depth
  const zs: number[] = [];
  eachVertex(root, (p) => {
    if (Math.abs(p.x) < 0.25 * sw && p.y < shoulderMid.y - 0.1 * sw && p.y > shoulderMid.y - 0.45 * sw) zs.push(p.z);
  });
  zs.sort((a, b) => a - b);
  const zMin = zs.length ? zs[Math.floor(zs.length * 0.05)] : shoulderMid.z - 0.2 * sw;
  const zMax = zs.length ? zs[Math.floor(zs.length * 0.95)] : shoulderMid.z + 0.2 * sw;
  const hips = pos(humanoid, "hips");
  const torso = { center: new Vector3(0, (hips.y + shoulderMid.y) / 2, (zMin + zMax) / 2), ax: 0.62 * sw, az: Math.max(0.5 * (zMax - zMin), 0.25 * sw), yMin: hips.y, yMax: shoulderMid.y + 0.15 * sw };
  return { shoulder, shoulderMid, sw, armLen, mouth, eyes, head, torso, mouthFrom: m ? "morph" : "estimate" };
}
