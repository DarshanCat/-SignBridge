import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { VRMLoaderPlugin, type VRM } from "@pixiv/three-vrm";
import { Texture, TextureLoader, type Object3D } from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { vi } from "vitest";
import { measureAnatomy, type Anatomy } from "./anatomy";
import { parseClip, type SignClip } from "./clip";
import type { MixamoRig } from "./mixamo";
import { buildVrmRig } from "./vrmRig";

/** Helpers for tests that need the real VRM and the real clips (all skipped when those git-ignored files are absent). */
const PUBLIC = join(process.cwd(), "public");
export const VRM_PATH = join(PUBLIC, "avatar", "signer.vrm");
export const clipPath = (name: string) => join(PUBLIC, "animations", `${name}.json`);
export const hasVrm = existsSync(VRM_PATH);
export const hasClip = (name: string) => existsSync(clipPath(name));

/** Clips used for measurements: a mix of signs at the face, at the chest and in front of the body. */
export const MEASURE_CLIPS = ["hello", "thank-you", "good", "doctor", "hospital", "market", "yesterday", "book", "bank", "teacher"];

export interface LoadedAvatar {
  vrm: VRM;
  root: Object3D;
  rig: MixamoRig;
  anatomy: Anatomy;
}

let cached: Promise<LoadedAvatar> | undefined;

/** Load signer.vrm in node (textures are replaced by empty ones: node cannot decode images, and no test needs them). */
export function loadAvatar(): Promise<LoadedAvatar> {
  cached ??= new Promise<LoadedAvatar>((res, rej) => {
    const hadSelf = "self" in globalThis;
    if (!hadSelf) (globalThis as { self?: unknown }).self = globalThis;
    vi.spyOn(TextureLoader.prototype, "load").mockImplementation(((_u: string, onLoad?: (t: Texture) => void) => {
      const t = new Texture();
      onLoad?.(t);
      return t;
    }) as never);
    const buf = readFileSync(VRM_PATH);
    const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer;
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));
    loader.parse(
      ab,
      "",
      (g) => {
        const vrm = g.userData.vrm as VRM | undefined;
        if (!vrm) return rej(new Error("not a VRM"));
        vrm.scene.updateMatrixWorld(true);
        const rig = buildVrmRig(vrm.scene, vrm.humanoid);
        res({ vrm, root: vrm.scene, rig, anatomy: measureAnatomy(vrm.scene, vrm.humanoid, rig) });
      },
      rej,
    );
  });
  return cached;
}

export function loadClip(name: string): SignClip {
  return parseClip(JSON.parse(readFileSync(clipPath(name), "utf-8")));
}
