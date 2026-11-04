"use client";
import { VRMLoaderPlugin, VRMUtils, type VRM } from "@pixiv/three-vrm";
import { useGLTF } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo } from "react";
import { Color, NoToneMapping, PointLight, type Material, type Mesh, type ToneMapping, type WebGLRenderer } from "three";
import { ExpressionSmoother, Blinker, nmmFaceTargets } from "@/lib/avatar/face";
import { PoseSmoother, withRelaxedRest } from "@/lib/avatar/idle";
import { applyMixamoPose } from "@/lib/avatar/mixamo";
import type { SequencePlayer } from "@/lib/avatar/player";
import { measureAnatomy } from "@/lib/avatar/anatomy";
import { SignRetargeter } from "@/lib/avatar/retarget";
import { makeSampler } from "@/lib/avatar/solverSampler";
import { buildVrmRig } from "@/lib/avatar/vrmRig";
import { useReducedMotion } from "./useReducedMotion";

/** Smoothing time constants in seconds: short inside a sign, longer for transitions. */
export const SIGN_TAU = 0.025;
/** Intensity of the soft light that rides on each hand (kept low: it only has to lift the hands off the shirt). */
export const HAND_LIGHT = 0.12;
export const TRANSITION_TAU = 0.07;

export const VRM_URL = "/avatar/signer.vrm";

/** Outline of the toon materials: a little wider than the model's own and tinted from the base colour instead of pure black, so it reads as a soft ink line. */
export const OUTLINE = { widthScale: 1.8, bodySkinWidth: 0.0032, minWidth: 0.0012, maxWidth: 0.003, darken: 0.38, mix: 1 } as const;

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
      const bodySkin = /Body.*SKIN/i.test(m.name); // the hands are part of the body skin: a firmer, warmer line separates them from the shirt
      if (bodySkin) m.outlineWidthFactor = OUTLINE.bodySkinWidth;
      const base = m.color ?? new Color("#ffffff");
      m.outlineColorFactor = bodySkin ? new Color("#b0666f") : base.clone().multiplyScalar(OUTLINE.darken).lerp(new Color("#3b2d52"), 0.25);
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
  const retargeter = useMemo(() => new SignRetargeter(rig, measureAnatomy(vrm.scene, vrm.humanoid, rig)), [vrm, rig]);
  const blinker = useMemo(() => new Blinker(), []);
  const face = useMemo(() => new ExpressionSmoother(), []);

  useEffect(() => {
    styleToonMaterials(vrm.scene);
    const tone = gl.toneMapping;
    setToneMapping(gl, NoToneMapping); // MToon draws its own shading; film tone mapping would wash out the toon bands
    onReady?.();
    return () => setToneMapping(gl, tone);
  }, [vrm, gl, onReady]);

  // the clips are retargeted onto this body at run time (its shoulders, mouth, head and arm lengths); a clip without source landmarks plays as before
  useEffect(() => {
    // ?legacy-retarget plays the clips' own tracks (for comparisons); the default is the retargeter
    if (new URLSearchParams(window.location.search).has("legacy-retarget")) return;
    player.setSampler(makeSampler(retargeter));
    return () => player.setSampler(null);
  }, [player, retargeter]);

  // a soft light rides on each hand, so the hands catch a highlight and stand out from the shirt and the hair
  useEffect(() => {
    const lights: PointLight[] = [];
    for (const name of ["leftHand", "rightHand"]) {
      const bone = vrm.humanoid.getNormalizedBoneNode(name as never);
      if (!bone) continue;
      const light = new PointLight(0xfff1f6, HAND_LIGHT, 0.45, 2);
      light.position.set(0, 0.02, 0.1);
      bone.add(light);
      lights.push(light);
    }
    return () => lights.forEach((l) => l.removeFromParent());
  }, [vrm]);

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    player.tick(dt);
    const target = withRelaxedRest(player.pose(), state.clock.elapsedTime, calm);
    // inside a sign the pose follows the source closely (crisp handshapes); between signs and at the ends it is smoothed more
    const smooth = smoother.step(target.pose, target.spread, dt, player.phase() === "sign" ? SIGN_TAU : TRANSITION_TAU);
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
