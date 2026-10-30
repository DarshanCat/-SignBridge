"use client";
import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Component, type ReactNode } from "react";
import type { SequencePlayer } from "@/lib/avatar/player";
import { Humanoid } from "./Humanoid";

function webglAvailable(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

function Fallback({ message }: { message: string }) {
  return (
    <div role="alert" className="flex h-full items-center justify-center p-6 text-center text-sm text-amber-200">
      {message}
    </div>
  );
}

class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? <Fallback message="The 3D avatar failed to render. Sign glosses are still shown as text." /> : this.props.children;
  }
}

export default function AvatarViewer({ player }: { player: SequencePlayer }) {
  if (typeof document !== "undefined" && !webglAvailable()) {
    return <Fallback message="WebGL is not available in this browser, so the 3D avatar cannot be shown. Sign glosses are still shown as text." />;
  }
  return (
    <SceneBoundary>
      <Canvas shadows dpr={[1, 2]} camera={{ position: [0, 1.5, 3.2], fov: 40 }} aria-label="3D signing avatar">
        <color attach="background" args={["#0b1020"]} />
        <hemisphereLight args={["#cbd5e1", "#1e293b", 0.9]} />
        <directionalLight position={[2, 4, 3]} intensity={1.6} castShadow shadow-mapSize={[1024, 1024]} />
        <Humanoid player={player} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.0, 0]} receiveShadow>
          <circleGeometry args={[1.6, 48]} />
          <meshStandardMaterial color="#121a33" roughness={1} />
        </mesh>
        <OrbitControls target={[0, 1.35, 0]} enablePan={false} minDistance={1.5} maxDistance={6} maxPolarAngle={Math.PI * 0.52} />
      </Canvas>
    </SceneBoundary>
  );
}
