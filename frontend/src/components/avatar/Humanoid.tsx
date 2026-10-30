"use client";
import { useFrame } from "@react-three/fiber";
import { useState } from "react";
import type { Group } from "three";
import { RIG, type RigNode, type Shape } from "@/lib/avatar/rig";
import type { SequencePlayer } from "@/lib/avatar/player";

const SKIN = "#c68f6d";
const CLOTH = "#334155";
const isSkin = (name: string) => name === "head" || name === "neck" || name.startsWith("hand_");

function Geometry({ shape }: { shape: Shape }) {
  if (shape.kind === "box") return <boxGeometry args={shape.size} />;
  if (shape.kind === "sphere") return <sphereGeometry args={[shape.radius, 24, 16]} />;
  return <capsuleGeometry args={[shape.radius, shape.length, 6, 12]} />;
}

function Bone({ node, children, register }: { node: RigNode; children: React.ReactNode; register: (n: string, g: Group | null) => void }) {
  return (
    <group ref={(g) => register(node.name, g)} position={node.offset}>
      {node.shape && (
        <mesh position={node.shapeOffset ?? [0, 0, 0]} castShadow>
          <Geometry shape={node.shape} />
          <meshStandardMaterial color={isSkin(node.name) ? SKIN : CLOTH} roughness={0.7} metalness={0.05} />
        </mesh>
      )}
      {children}
    </group>
  );
}

function renderTree(parent: string | null, register: (n: string, g: Group | null) => void): React.ReactNode {
  return RIG.filter((n) => n.parent === parent).map((n) => (
    <Bone key={n.name} node={n} register={register}>
      {renderTree(n.name, register)}
    </Bone>
  ));
}

/** Procedural humanoid. Each frame it advances the player and applies the current pose; bones without a track return to rest. */
export function Humanoid({ player }: { player: SequencePlayer }) {
  const [bones] = useState(() => new Map<string, Group>());
  const tree = renderTree(null, (name, g) => {
    if (g) bones.set(name, g);
    else bones.delete(name);
  });

  useFrame((_, delta) => {
    player.tick(Math.min(delta, 0.1));
    const pose = player.pose();
    bones.forEach((g, name) => {
      const r = pose[name];
      g.rotation.set(r ? r[0] : 0, r ? r[1] : 0, r ? r[2] : 0);
    });
  });

  return <>{tree}</>;
}
