"use client";
import { useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { Component, useEffect, useMemo, type ReactNode } from "react";
import type { Mesh } from "three";
import { clone } from "three/examples/jsm/utils/SkeletonUtils.js";
import { applyMixamoPose, buildMixamoRig } from "@/lib/avatar/mixamo";
import type { SequencePlayer } from "@/lib/avatar/player";
import { Humanoid } from "./Humanoid";

export const AVATAR_URL = "/avatar/signer.glb";
export type AvatarKind = "glb" | "procedural";

/** Mixamo rigged avatar driven by SignBridge clips. Throws (caught by GlbBoundary) if the file or its skeleton is unusable. */
function GlbModel({ player, onKind }: { player: SequencePlayer; onKind?: (k: AvatarKind) => void }) {
  const { scene } = useGLTF(AVATAR_URL, false); // false: never fetch a Draco decoder from a CDN
  const model = useMemo(() => clone(scene), [scene]);
  const rig = useMemo(() => buildMixamoRig(model), [model]);

  useEffect(() => {
    model.traverse((o) => {
      if ((o as Mesh).isMesh) o.castShadow = true;
    });
    onKind?.("glb");
  }, [model, onKind]);

  useFrame((_, delta) => {
    player.tick(Math.min(delta, 0.1));
    applyMixamoPose(rig, player.pose());
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
  render() {
    return this.state.failed ? <Fallback player={this.props.player} onKind={this.props.onKind} /> : this.props.children;
  }
}

/** The Mixamo avatar if /avatar/signer.glb loads and has the required bones, otherwise the procedural humanoid. */
export function SignerAvatar({ player, onKind }: { player: SequencePlayer; onKind?: (k: AvatarKind) => void }) {
  return (
    <GlbBoundary player={player} onKind={onKind}>
      <GlbModel player={player} onKind={onKind} />
    </GlbBoundary>
  );
}
