"use client";
import { VRMLoaderPlugin, VRMUtils, type VRM } from "@pixiv/three-vrm";
import { useGLTF } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import { Color, NoToneMapping, type Material, type Mesh, type ToneMapping, type WebGLRenderer } from "three";
import { ExpressionSmoother, Blinker, nmmFaceTargets } from "@/lib/avatar/face";
import { PoseSmoother, withRelaxedRest } from "@/lib/avatar/idle";
import { applyMixamoPose } from "@/lib/avatar/mixamo";
import type { SequencePlayer } from "@/lib/avatar/player";
import { buildVrmRig } from "@/lib/avatar/vrmRig";
import { useReducedMotion } from "./useReducedMotion";

export const VRM_URL = "/avatar/signer.vrm";

/** Outline of the toon materials: a little wider than the model's own and tinted from the base colour instead of pure black, so it reads as a soft ink line. */
export const OUTLINE = { widthScale: 1.8, minWidth: 0.0012, maxWidth: 0.003, darken: 0.38, mix: 1 } as const;

type MToonLike = Material & {
  isOutline?: boolean;
  outlineWidthMode?: string;
  outlineWidthFactor?: number;
  outlineColorFactor?: Color;
  outlineLightingMixFactor?: number;
  color?: Color;
  shadeColorFactor?: Color;
};

/** Soften the outline of the VRM's own MToon materials. Materials without an outline in the file are left alone. */
export function styleToonMaterials(root: { traverse(cb: (o: unknown) => void): void }): number {
  let touched = 0;
  root.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh) return;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    for (const m of (Array.isArray(mesh.material) ? mesh.material : [mesh.material]) as MToonLike[]) {
      if (!m.isOutline || m.outlineWidthFactor === undefined) continue;
      m.outlineWidthFactor = Math.min(OUTLINE.maxWidth, Math.max(OUTLINE.minWidth, m.outlineWidthFactor * OUTLINE.widthScale));
      const base = m.color ?? new Color("#ffffff");
      m.outlineColorFactor = base.clone().multiplyScalar(OUTLINE.darken).lerp(new Color("#3b2d52"), 0.25);
      m.outlineLightingMixFactor = OUTLINE.mix;
      m.needsUpdate = true;
      touched++;
    }
  });
  return touched;
}

function setToneMapping(renderer: WebGLRenderer, mapping: ToneMapping): void {
  renderer.toneMapping = mapping;
}

/** One time clean up of a loaded VRM (the loader caches it, so the hook may run more than once). */
function prepareVrm(vrm: VRM): void {
  if (vrm.scene.userData.signbridgePrepared) return;
  VRMUtils.removeUnnecessaryVertices(vrm.scene);
  VRMUtils.combineSkeletons(vrm.scene);
  VRMUtils.rotateVRM0(vrm); // no-op for VRM 1.0; turns a VRM 0.x model to face +z
  vrm.scene.userData.signbridgePrepared = true;
}

function useVrm(): VRM {
  const gltf = useGLTF(VRM_URL, false, false, (loader) => {
    // drei's loader comes from three-stdlib and three-vrm is typed against three's own GLTFLoader; the objects are compatible at run time
    (loader as unknown as { register(cb: (parser: unknown) => unknown): void }).register((parser) => new VRMLoaderPlugin(parser as never));
  });
  const vrm = gltf.userData.vrm as VRM | undefined;
  if (!vrm) throw new Error(`${VRM_URL} is not a VRM file`);
  prepareVrm(vrm);
  return vrm;
}

/** Anime avatar (VRM) driven by the same clips, idle layer and smoothing as the Mixamo model. Throws if the file or its humanoid is unusable. */
export function VrmModel({ player, onReady }: { player: SequencePlayer; onReady?: () => void }) {
  const vrm = useVrm();
  const calm = useReducedMotion();
  const gl = useThree((s) => s.gl);
  const rig = useMemo(() => {
    vrm.scene.updateMatrixWorld(true);
    return buildVrmRig(vrm.scene, vrm.humanoid);
  }, [vrm]);
  const smoother = useMemo(() => new PoseSmoother(), []);
  const blinker = useMemo(() => new Blinker(), []);
  const face = useMemo(() => new ExpressionSmoother(), []);

  useEffect(() => {
    styleToonMaterials(vrm.scene);
    const tone = gl.toneMapping;
    setToneMapping(gl, NoToneMapping); // MToon draws its own shading; film tone mapping would wash out the toon bands
    onReady?.();
    return () => setToneMapping(gl, tone);
  }, [vrm, gl, onReady]);

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    player.tick(dt);
    const target = withRelaxedRest(player.pose(), state.clock.elapsedTime, calm);
    const smooth = smoother.step(target.pose, target.spread, dt);
    applyMixamoPose(rig, smooth.pose, smooth.spread);
    const em = vrm.expressionManager;
    if (em) {
      const f = face.step(nmmFaceTargets(player.nmmState()), dt);
      em.setValue("neutral", 1); // neutral face while signing; only the rule-based markers and blinking change it
      em.setValue("blink", blinker.step(dt));
      em.setValue("surprised", f.surprised);
      em.setValue("sad", f.sad);
    }
    vrm.update(dt); // copies the normalized pose to the skeleton, then expressions, look-at and spring bones (hair, cloth)
  });

  return <primitive object={vrm.scene} />;
}
