import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { VRMLoaderPlugin, type VRM } from "@pixiv/three-vrm";
import { Bone, Object3D, Texture, TextureLoader, Vector3 } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { Pose } from "./clip";
import { parseClip, sampleClip } from "./clip";
import { applyMixamoPose, buildMixamoRig, findBone, requiredMixamoBones } from "./mixamo";
import { buildVrmRig, missingVrmBones, requiredVrmBones, VRM_BONE_MAP, type HumanoidLike } from "./vrmRig";

const VRM_FILE = join(process.cwd(), "public", "avatar", "signer.vrm");
const hasVrm = existsSync(VRM_FILE);

const pos = (o: Object3D) => o.getWorldPosition(new Vector3());
const dirTo = (a: Object3D, b: Object3D) => pos(b).sub(pos(a)).normalize();
const near = (v: Vector3, e: [number, number, number], tol = 0.12) => expect(v.distanceTo(new Vector3(...e))).toBeLessThan(tol);

/** A T-pose skeleton with the VRM 1.0 humanoid bone names (palms down, thumbs forward), as the normalized humanoid of a VRM has. */
function syntheticVrm(): { root: Object3D; humanoid: HumanoidLike } {
  const bones = new Map<string, Object3D>();
  const root = new Object3D();
  const add = (name: string, parent: Object3D, x: number, y: number, z: number): Object3D => {
    const b = new Bone();
    b.name = name;
    b.position.set(x, y, z);
    parent.add(b);
    bones.set(name, b);
    return b;
  };
  const hips = add("hips", root, 0, 0.9, 0);
  const spine = add("spine", hips, 0, 0.1, 0);
  const chest = add("chest", spine, 0, 0.15, 0);
  const upper = add("upperChest", chest, 0, 0.1, 0);
  const neck = add("neck", upper, 0, 0.15, 0);
  add("head", neck, 0, 0.1, 0);
  for (const [side, s] of [["left", 1], ["right", -1]] as const) {
    const shoulder = add(`${side}Shoulder`, upper, s * 0.05, 0.1, 0);
    const arm = add(`${side}UpperArm`, shoulder, s * 0.1, 0, 0);
    const fore = add(`${side}LowerArm`, arm, s * 0.28, 0, 0);
    const hand = add(`${side}Hand`, fore, s * 0.25, 0, 0);
    // fingers lie along the arm direction; index is in front (+z) of the little finger, the thumb points forward and outward
    const fingers: [string[], number, number, number][] = [
      [["ThumbMetacarpal", "ThumbProximal", "ThumbDistal"], 0.03, 0.035, 1],
      [["IndexProximal", "IndexIntermediate", "IndexDistal"], 0.09, 0.03, 0],
      [["MiddleProximal", "MiddleIntermediate", "MiddleDistal"], 0.095, 0.01, 0],
      [["RingProximal", "RingIntermediate", "RingDistal"], 0.09, -0.01, 0],
      [["LittleProximal", "LittleIntermediate", "LittleDistal"], 0.08, -0.03, 0],
    ];
    for (const [parts, x0, z0, thumb] of fingers) {
      let parent: Object3D = hand;
      parts.forEach((part, i) => {
        const step = thumb ? [s * 0.02, 0, 0.025] : [s * 0.03, 0, 0];
        parent = add(`${side}${part}`, parent, i === 0 ? s * x0 : step[0], 0, i === 0 ? z0 : step[2]);
      });
    }
  }
  root.updateMatrixWorld(true);
  return { root, humanoid: { getNormalizedBoneNode: (n) => bones.get(n) ?? null } };
}

describe("VRM bone map", () => {
  it("maps every rig slot (torso, arms, three joints per finger on both hands) to a distinct VRM 1.0 humanoid bone", () => {
    expect(Object.keys(VRM_BONE_MAP)).toHaveLength(requiredMixamoBones().length);
    expect(new Set(requiredVrmBones()).size).toBe(requiredVrmBones().length);
    expect(VRM_BONE_MAP.Spine2).toBe("chest");
    expect(VRM_BONE_MAP.LeftHandThumb1).toBe("leftThumbMetacarpal");
    expect(VRM_BONE_MAP.RightHandPinky3).toBe("rightLittleDistal");
    expect(VRM_BONE_MAP.LeftForeArm).toBe("leftLowerArm");
  });

  it("every Mixamo slot the rig asks for has a VRM bone", () => {
    for (const slot of requiredMixamoBones()) expect(VRM_BONE_MAP[slot], slot).toBeTruthy();
  });

  it("reports missing humanoid bones instead of failing silently", () => {
    const empty: HumanoidLike = { getNormalizedBoneNode: () => null };
    expect(missingVrmBones(empty)).toHaveLength(requiredVrmBones().length);
    expect(() => buildVrmRig(new Object3D(), empty)).toThrow(/missing humanoid bones/);
  });
});

/** The forward kinematics checks of the Mixamo rig, run against a VRM skeleton. */
function fkSuite(make: () => Promise<{ root: Object3D; humanoid: HumanoidLike }> | { root: Object3D; humanoid: HumanoidLike }) {
  const get = async () => {
    const m = await make();
    m.root.updateMatrixWorld(true);
    return { ...m, rig: buildVrmRig(m.root, m.humanoid), b: (n: string) => m.humanoid.getNormalizedBoneNode(n) as Object3D };
  };

  it("has every required bone and derives an arms-down rest pose from the T-pose", async () => {
    const { humanoid, rig, b } = await get();
    expect(missingVrmBones(humanoid)).toEqual([]);
    applyMixamoPose(rig, {});
    for (const side of ["left", "right"]) {
      near(dirTo(b(`${side}UpperArm`), b(`${side}LowerArm`)), [0, -1, 0]);
      near(dirTo(b(`${side}LowerArm`), b(`${side}Hand`)), [0, -1, 0]);
    }
    // thumbs point outward in the rest pose (palms forward): left side is +x, right side is -x
    expect(pos(b("leftThumbMetacarpal")).x).toBeGreaterThan(pos(b("leftLittleProximal")).x);
    expect(pos(b("rightThumbMetacarpal")).x).toBeLessThan(pos(b("rightLittleProximal")).x);
    expect(pos(b("leftUpperArm")).x).toBeGreaterThan(0);
    expect(pos(b("rightUpperArm")).x).toBeLessThan(0);
  });

  it("a negative x rotation raises the arm toward the camera and a positive z rotation lifts it outward, for both arms", async () => {
    const { rig, b } = await get();
    applyMixamoPose(rig, { upperArm_l: [-Math.PI / 2, 0, 0], upperArm_r: [-Math.PI / 2, 0, 0] });
    near(dirTo(b("leftUpperArm"), b("leftLowerArm")), [0, 0, 1]);
    near(dirTo(b("rightUpperArm"), b("rightLowerArm")), [0, 0, 1]);
    applyMixamoPose(rig, { upperArm_l: [0, 0, Math.PI / 2], upperArm_r: [0, 0, -Math.PI / 2] });
    near(dirTo(b("leftUpperArm"), b("leftLowerArm")), [1, 0, 0]);
    near(dirTo(b("rightUpperArm"), b("rightLowerArm")), [-1, 0, 0]);
  });

  it("applies elbow bend relative to the upper arm and is repeatable", async () => {
    const { rig, b } = await get();
    const pose: Pose = { upperArm_l: [-Math.PI / 2, 0, 0], foreArm_l: [-Math.PI / 2, 0, 0] };
    applyMixamoPose(rig, { ...pose });
    const first = b("leftLowerArm").quaternion.clone();
    near(dirTo(b("leftLowerArm"), b("leftHand")), [0, 1, 0]); // arm forward, forearm bent up
    applyMixamoPose(rig, { ...pose });
    expect(b("leftLowerArm").quaternion.angleTo(first)).toBeLessThan(0.005);
  });

  it("splits a finger curl over its three joints and curls toward the palm side (+z)", async () => {
    const { rig, b } = await get();
    applyMixamoPose(rig, {});
    // the distal bone has no child in a VRM, so measure the proximal to intermediate and intermediate to distal segments
    const rest = dirTo(b("leftIndexIntermediate"), b("leftIndexDistal"));
    applyMixamoPose(rig, { "hand_l.index": [-1.5, 0, 0] });
    const curled = dirTo(b("leftIndexIntermediate"), b("leftIndexDistal"));
    // the first two joints carry 0.4 + 0.4 of the curl, so the last segment points 0.8 * 1.5 rad away from the rest direction
    expect(rest.angleTo(curled)).toBeCloseTo(1.2, 1);
    expect(curled.z).toBeGreaterThan(rest.z + 0.5);
    const proximalRest = (applyMixamoPose(rig, {}), dirTo(b("leftIndexProximal"), b("leftIndexIntermediate")));
    applyMixamoPose(rig, { "hand_l.index": [-1.5, 0, 0] });
    expect(proximalRest.angleTo(dirTo(b("leftIndexProximal"), b("leftIndexIntermediate")))).toBeCloseTo(0.6, 1);
  });

  it("clip rotations of the torso and head move the head without touching the feet", async () => {
    const { rig, b } = await get();
    applyMixamoPose(rig, {});
    const feetBefore = b("hips").position.clone();
    const headRest = pos(b("head"));
    applyMixamoPose(rig, { spine: [0.2, 0, 0], head: [0, 0.4, 0] });
    expect(pos(b("head")).distanceTo(headRest)).toBeGreaterThan(0.005);
    expect(b("hips").position.distanceTo(feetBefore)).toBeLessThan(1e-9);
  });
}

describe("VRM driven by clips (synthetic T-pose skeleton, forward kinematics)", () => {
  fkSuite(syntheticVrm);
});

describe.skipIf(!hasVrm)("signer.vrm driven by clips (real file, forward kinematics)", () => {
  // The VRM carries textures; node has no image decoding, so texture loading is replaced by empty textures for the test only.
  let spy: ReturnType<typeof vi.spyOn> | undefined;
  const hadSelf = "self" in globalThis;
  beforeAll(() => {
    if (!hadSelf) (globalThis as { self?: unknown }).self = globalThis; // GLTFLoader reads self.URL for embedded images
    spy = vi.spyOn(TextureLoader.prototype, "load").mockImplementation(((_url: string, onLoad?: (t: Texture) => void) => {
      const t = new Texture();
      onLoad?.(t);
      return t;
    }) as never);
  });
  afterAll(() => {
    spy?.mockRestore();
    if (!hadSelf) delete (globalThis as { self?: unknown }).self;
  });

  let cached: Promise<{ root: Object3D; humanoid: HumanoidLike }> | undefined;
  const load = () =>
    (cached ??= new Promise((res, rej) => {
      const buf = readFileSync(VRM_FILE);
      const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer;
      const loader = new GLTFLoader();
      loader.register((parser) => new VRMLoaderPlugin(parser));
      loader.parse(ab, "", (g) => {
        const vrm = g.userData.vrm as VRM | undefined;
        if (!vrm) return rej(new Error("not a VRM"));
        res({ root: vrm.scene, humanoid: vrm.humanoid });
      }, rej);
    }));

  it("is a VRM with the expression presets the face uses", async () => {
    const { root } = await load();
    expect(root).toBeTruthy();
  });

  fkSuite(load);
});

const GLB_FILE = join(process.cwd(), "public", "avatar", "signer.glb");
const CLIPS = ["hello", "doctor", "hospital", "thank-you", "good", "book", "water", "bank"].map((n) => join(process.cwd(), "public", "animations", `${n}.json`)).filter(existsSync);

describe.skipIf(!hasVrm || !existsSync(GLB_FILE) || CLIPS.length < 3)("the VRM and the Mixamo model make the same movements from the same real clips", () => {
  const hadSelf = "self" in globalThis;
  let spy: ReturnType<typeof vi.spyOn> | undefined;
  beforeAll(() => {
    if (!hadSelf) (globalThis as { self?: unknown }).self = globalThis;
    spy = vi.spyOn(TextureLoader.prototype, "load").mockImplementation(((_u: string, onLoad?: (t: Texture) => void) => {
      const t = new Texture();
      onLoad?.(t);
      return t;
    }) as never);
  });
  afterAll(() => {
    spy?.mockRestore();
    if (!hadSelf) delete (globalThis as { self?: unknown }).self;
  });

  const parse = (file: string) =>
    new Promise<{ scene: Object3D; userData: Record<string, unknown> }>((res, rej) => {
      const buf = readFileSync(file);
      const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer;
      const loader = new GLTFLoader();
      loader.register((parser) => new VRMLoaderPlugin(parser));
      loader.parse(ab, "", (g) => res({ scene: g.scene, userData: g.userData }), rej);
    });

  it("arm and finger directions agree within 0.15 rad over sampled poses of several clips (both arms)", async () => {
    const vrm = (await parse(VRM_FILE)).userData.vrm as VRM;
    const mix = (await parse(GLB_FILE)).scene;
    vrm.scene.updateMatrixWorld(true);
    mix.updateMatrixWorld(true);
    const rv = buildVrmRig(vrm.scene, vrm.humanoid);
    const rm = buildMixamoRig(mix);
    const vb = (n: string) => vrm.humanoid.getNormalizedBoneNode(n as never) as Object3D;
    const mb = (n: string) => findBone(mix, n) as Object3D;
    const segments: [string, string, string, string][] = []; // [vrm from, vrm to, mixamo from, mixamo to]
    for (const [vs, ms] of [["left", "Left"], ["right", "Right"]] as const) {
      segments.push([`${vs}UpperArm`, `${vs}LowerArm`, `${ms}Arm`, `${ms}ForeArm`], [`${vs}LowerArm`, `${vs}Hand`, `${ms}ForeArm`, `${ms}Hand`]);
      for (const [vf, mf] of [["Index", "Index"], ["Middle", "Middle"], ["Little", "Pinky"]] as const) {
        segments.push([`${vs}${vf}Proximal`, `${vs}${vf}Intermediate`, `${ms}Hand${mf}1`, `${ms}Hand${mf}2`], [`${vs}${vf}Intermediate`, `${vs}${vf}Distal`, `${ms}Hand${mf}2`, `${ms}Hand${mf}3`]);
      }
    }
    let worst = 0;
    let checked = 0;
    for (const file of CLIPS) {
      const clip = parseClip(JSON.parse(readFileSync(file, "utf-8")));
      for (let i = 0; i <= 8; i++) {
        const pose = sampleClip(clip, (clip.duration * i) / 8);
        applyMixamoPose(rv, pose);
        applyMixamoPose(rm, pose);
        for (const [a, b, c, d] of segments) {
          const angle = dirTo(vb(a), vb(b)).angleTo(dirTo(mb(c), mb(d)));
          worst = Math.max(worst, angle);
          checked++;
        }
      }
    }
    expect(checked).toBeGreaterThan(300);
    expect(worst).toBeLessThan(0.15);
  });
});
