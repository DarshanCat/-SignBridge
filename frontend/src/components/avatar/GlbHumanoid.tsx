"use client";
import { useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { Component, Suspense, useEffect, useMemo, type ReactNode } from "react";
import type { Mesh, MeshStandardMaterial } from "three";
import { clone } from "three/examples/jsm/utils/SkeletonUtils.js";
import { PoseSmoother, withRelaxedRest } from "@/lib/avatar/idle";
import { applyMixamoPose, buildMixamoRig } from "@/lib/avatar/mixamo";
import type { SequencePlayer } from "@/lib/avatar/player";
import { Humanoid } from "./Humanoid";
import { VrmModel } from "./VrmHumanoid";

export const AVATAR_URL = "/avatar/signer.glb";
export type AvatarKind = "vrm" | "glb" | "procedural";

/** Mixamo rigged avatar driven by SignBridge clips. Throws (caught by GlbBoundary) if the file or its skeleton is unusable. */
function GlbModel({ player, onKind }: { player: SequencePlayer; onKind?: (k: AvatarKind) => void }) {
  const { scene } = useGLTF(AVATAR_URL, false); // false: never fetch a Draco decoder from a CDN
  const model = useMemo(() => clone(scene), [scene]);
  const rig = useMemo(() => buildMixamoRig(model), [model]);

  const smoother = useMemo(() => new PoseSmoother(), []);

  useEffect(() => {
    model.traverse((o) => {
      const mesh = o as Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = true;
      mesh.receiveShadow = true; // arms and hands shade the body
      for (const m of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
        const std = m as MeshStandardMaterial;
        if (!std.isMeshStandardMaterial) continue;
        std.roughness = 0.62; // soft satin instead of the flat plastic look
        std.metalness = 0;
        std.envMapIntensity = 0.6;
        std.needsUpdate = true;
      }
    });
    onKind?.("glb");
  }, [model, onKind]);

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.1);
    player.tick(dt);
    const target = withRelaxedRest(player.pose(), state.clock.elapsedTime);
    const smooth = smoother.step(target.pose, target.spread, dt);
    applyMixamoPose(rig, smooth.pose, smooth.spread);
  });
  return <primitive object={model} />;
}

function Fallback({ player, onKind }: { player: SequencePlayer; onKind?: (k: AvatarKind) => void }) {
  useEffect(() => onKind?.("procedural"), [onKind]);
  return <Humanoid player={player} />;
}

class GlbBoundary extends Component<{ player: SequencePlayer; onKind?: (k: AvatarKind) => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error) {
    console.warn(`SignBridge avatar: ${error.message}; using the next fallback`);
  }
  render() {
    return this.state.failed ? <Fallback player={this.props.player} onKind={this.props.onKind} /> : this.props.children;
  }
}

/** Shows `fallback` when anything inside throws (the VRM is missing, is not a VRM, or lacks the humanoid bones). */
class ModelBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error) {
    console.warn(`SignBridge avatar: ${error.message}; using the next fallback`);
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

/**
 * The anime avatar if /avatar/signer.vrm loads and has the humanoid bones, otherwise the Mixamo avatar if /avatar/signer.glb loads, otherwise
 * the procedural humanoid.
 */
export function SignerAvatar({ player, onKind }: { player: SequencePlayer; onKind?: (k: AvatarKind) => void }) {
  const mixamoOrProcedural = (
    <GlbBoundary player={player} onKind={onKind}>
      <Suspense fallback={<Fallback player={player} onKind={onKind} />}>
        <GlbModel player={player} onKind={onKind} />
      </Suspense>
    </GlbBoundary>
  );
  return (
    <ModelBoundary fallback={mixamoOrProcedural}>
      <Suspense fallback={null}>
        <VrmModel player={player} onReady={() => onKind?.("vrm")} />
      </Suspense>
    </ModelBoundary>
  );
}
