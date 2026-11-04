import type { Object3D } from "three";
import { buildRigFromLookup, type MixamoRig } from "./mixamo";

/**
 * VRM humanoid rig. SignBridge clips name 20 bones (torso, arms, three joints per finger). The rig code addresses them through Mixamo style
 * slot names ("Spine2", "LeftArm", "LeftHandIndex1"); this table maps every slot to the VRM 1.0 humanoid bone. Fingers have three joints in
 * VRM 1.0 as well: the thumb is Metacarpal, Proximal, Distal, the other fingers Proximal, Intermediate, Distal (three-vrm converts VRM 0.x
 * models to these names). The rest pose is NOT assumed: buildVrmRig derives the arms-down pose from the positions of the loaded model's bones.
 *
 * The rig drives the NORMALIZED humanoid (a T-pose copy with identity rest rotations); vrm.update() copies it to the real skeleton, so
 * models with different bone roll all behave the same.
 */
const FINGER_PARTS: Record<string, [string, string, string]> = {
  Thumb: ["ThumbMetacarpal", "ThumbProximal", "ThumbDistal"],
  Index: ["IndexProximal", "IndexIntermediate", "IndexDistal"],
  Middle: ["MiddleProximal", "MiddleIntermediate", "MiddleDistal"],
  Ring: ["RingProximal", "RingIntermediate", "RingDistal"],
  Pinky: ["LittleProximal", "LittleIntermediate", "LittleDistal"],
};

function buildMap(): Record<string, string> {
  const map: Record<string, string> = { Spine: "spine", Spine2: "chest", Neck: "neck", Head: "head" };
  for (const [side, lower] of [["Left", "left"], ["Right", "right"]] as const) {
    map[`${side}Arm`] = `${lower}UpperArm`;
    map[`${side}ForeArm`] = `${lower}LowerArm`;
    map[`${side}Hand`] = `${lower}Hand`;
    for (const [finger, parts] of Object.entries(FINGER_PARTS)) {
      parts.forEach((part, i) => {
        map[`${side}Hand${finger}${i + 1}`] = lower + part;
      });
    }
  }
  return map;
}

/** Mixamo style slot name to VRM 1.0 humanoid bone name. */
export const VRM_BONE_MAP: Readonly<Record<string, string>> = buildMap();

/** The part of the three-vrm VRMHumanoid that the rig needs (so it can be tested with a plain skeleton). */
export interface HumanoidLike {
  getNormalizedBoneNode(name: string): Object3D | null;
}

export const requiredVrmBones = (): string[] => Object.values(VRM_BONE_MAP);

export function missingVrmBones(humanoid: HumanoidLike): string[] {
  return requiredVrmBones().filter((n) => !humanoid.getNormalizedBoneNode(n));
}

export function buildVrmRig(root: Object3D, humanoid: HumanoidLike): MixamoRig {
  const missing = missingVrmBones(humanoid);
  if (missing.length) throw new Error(`VRM is missing humanoid bones: ${missing.join(", ")}`);
  return buildRigFromLookup(root, (slot) => humanoid.getNormalizedBoneNode(VRM_BONE_MAP[slot]) as Object3D);
}
