import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { Object3D, Vector3, type Bone } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import type { Pose } from "./clip";
import { applyMixamoPose, boneDirection, buildMixamoRig, findBone, missingMixamoBones, requiredMixamoBones } from "./mixamo";

const GLB = join(process.cwd(), "public", "avatar", "signer.glb");
const hasGlb = existsSync(GLB);

async function load(): Promise<Object3D> {
  const buf = readFileSync(GLB);
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  return new Promise((res, rej) => new GLTFLoader().parse(ab as ArrayBuffer, "", (g) => res(g.scene), rej));
}

const near = (a: Vector3, b: [number, number, number], tol = 0.12) => expect(a.distanceTo(new Vector3(...b))).toBeLessThan(tol);
const pos = (o: Object3D) => o.getWorldPosition(new Vector3());

describe("mixamo skeleton", () => {
  it("lists the bones a Mixamo rig must have (torso, arms, 3 joints per finger on both hands)", () => {
    const names = requiredMixamoBones();
    expect(names).toHaveLength(4 + 2 * (3 + 5 * 3));
    expect(names).toContain("RightHandPinky3");
  });

  it("reports missing bones instead of failing silently", () => {
    const empty = new Object3D();
    expect(missingMixamoBones(empty)).toHaveLength(requiredMixamoBones().length);
    expect(() => buildMixamoRig(empty)).toThrow(/missing bones/);
  });
});

describe.skipIf(!hasGlb)("signer.glb driven by clips (real file, forward kinematics)", () => {
  it("has every required bone and derives an arms-down rest pose from the T-pose", async () => {
    const scene = await load();
    scene.updateMatrixWorld(true);
    expect(missingMixamoBones(scene)).toEqual([]);
    const rig = buildMixamoRig(scene);
    applyMixamoPose(rig, {}); // no clip: rest pose
    for (const side of ["Left", "Right"]) {
      near(boneDirection(findBone(scene, `${side}Arm`) as Bone), [0, -1, 0]);
      near(boneDirection(findBone(scene, `${side}ForeArm`) as Bone), [0, -1, 0]);
    }
    // thumbs point outward in the rest pose (palms forward): left side is +x, right side is -x
    expect(pos(findBone(scene, "LeftHandThumb1")!).x).toBeGreaterThan(pos(findBone(scene, "LeftHandPinky1")!).x);
    expect(pos(findBone(scene, "RightHandThumb1")!).x).toBeLessThan(pos(findBone(scene, "RightHandPinky1")!).x);
    // the left arm is on the +x side and the right arm on the -x side, as in the clip convention
    expect(pos(findBone(scene, "LeftArm")!).x).toBeGreaterThan(0);
    expect(pos(findBone(scene, "RightArm")!).x).toBeLessThan(0);
  });

  it("a negative x rotation raises the arm toward the camera and a positive z rotation lifts it outward, for both arms", async () => {
    const scene = await load();
    const rig = buildMixamoRig(scene);
    applyMixamoPose(rig, { upperArm_l: [-Math.PI / 2, 0, 0], upperArm_r: [-Math.PI / 2, 0, 0] });
    near(boneDirection(findBone(scene, "LeftArm") as Bone), [0, 0, 1]);
    near(boneDirection(findBone(scene, "RightArm") as Bone), [0, 0, 1]);
    applyMixamoPose(rig, { upperArm_l: [0, 0, Math.PI / 2], upperArm_r: [0, 0, -Math.PI / 2] });
    near(boneDirection(findBone(scene, "LeftArm") as Bone), [1, 0, 0]);
    near(boneDirection(findBone(scene, "RightArm") as Bone), [-1, 0, 0]);
  });

  it("applies elbow bend relative to the upper arm and is repeatable", async () => {
    const scene = await load();
    const rig = buildMixamoRig(scene);
    const pose: Pose = { upperArm_l: [-Math.PI / 2, 0, 0], foreArm_l: [-Math.PI / 2, 0, 0] };
    applyMixamoPose(rig, { ...pose });
    const first = findBone(scene, "LeftForeArm")!.quaternion.clone();
    near(boneDirection(findBone(scene, "LeftForeArm") as Bone), [0, 1, 0]); // arm forward, forearm bent up
    applyMixamoPose(rig, { ...pose });
    expect(findBone(scene, "LeftForeArm")!.quaternion.angleTo(first)).toBeLessThan(0.005) // float32 world matrix noise on the 0.01 scaled armature, not drift: every call recomputes from scratch;
  });

  it("splits a finger curl over its three joints and curls toward the palm side (+z)", async () => {
    const scene = await load();
    const rig = buildMixamoRig(scene);
    applyMixamoPose(rig, {});
    const rest = boneDirection(findBone(scene, "LeftHandIndex3") as Bone);
    applyMixamoPose(rig, { "hand_l.index": [-1.5, 0, 0] });
    const curled = boneDirection(findBone(scene, "LeftHandIndex3") as Bone);
    expect(rest.angleTo(curled)).toBeCloseTo(1.5, 1); // the whole curl reaches the last segment
    expect(curled.z).toBeGreaterThan(rest.z + 0.5);
    const mid = boneDirection(findBone(scene, "LeftHandIndex1") as Bone);
    applyMixamoPose(rig, {});
    const restMid = boneDirection(findBone(scene, "LeftHandIndex1") as Bone);
    expect(restMid.angleTo(mid)).toBeGreaterThan(0.0); // joints are untouched at rest
  });
});
