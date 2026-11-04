"use client";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Component, Suspense, useCallback, useEffect, useState, type ReactNode } from "react";
import type { Camera, Vector3 } from "three";
import { useThree } from "@react-three/fiber";
import type { SequencePlayer } from "@/lib/avatar/player";
import { SignerAvatar, type AvatarKind } from "./GlbHumanoid";
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

/** Camera and orbit target per avatar: the anime avatar is framed from the waist up so that the face and both hands fill the stage. */
export const FRAMING = {
  vrm: { position: [0, 1.32, 1.72], target: [0, 1.18, 0] },
  other: { position: [0, 1.3, 2.45], target: [0, 1.25, 0] },
} as const;

function setFraming(camera: Camera, controls: { target: Vector3; update(): void } | null, f: { position: readonly number[]; target: readonly number[] }): void {
  camera.position.set(f.position[0], f.position[1], f.position[2]);
  if (controls) {
    controls.target.set(f.target[0], f.target[1], f.target[2]);
    controls.update();
  }
}

function Framing({ kind }: { kind: AvatarKind | null }) {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as { target: Vector3; update(): void } | null;
  useEffect(() => {
    setFraming(camera, controls, kind === "vrm" ? FRAMING.vrm : FRAMING.other);
  }, [kind, camera, controls]);
  return null;
}

/** Soft anime style lighting for the toon (MToon) materials: a gentle warm key, a pink fill, a cool rim and plenty of ambient light so the shade bands stay light. */
function AnimeLights() {
  return (
    <>
      <ambientLight intensity={0.95} color="#fff4f0" />
      <hemisphereLight args={["#ffe9f0", "#9fb4e6", 0.55]} />
      <directionalLight
        position={[-1.4, 2.8, 2.8]}
        intensity={1.5}
        color="#fff3e6"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-radius={6}
        shadow-bias={-0.0004}
        shadow-normalBias={0.02}
        shadow-camera-left={-1.6}
        shadow-camera-right={1.6}
        shadow-camera-top={2.4}
        shadow-camera-bottom={-0.4}
        shadow-camera-near={0.5}
        shadow-camera-far={9}
      />
      <directionalLight position={[2.4, 1.4, 2.2]} intensity={0.4} color="#ffc9dc" />
      <directionalLight position={[1.2, 2.4, -2.4]} intensity={0.9} color="#b8d6ff" />
    </>
  );
}

function StudioLights() {
  return (
    <>
      {/* three point lighting: warm key from the front left above, cool fill from the right, rim from behind to separate the head and shoulders */}
      <hemisphereLight args={["#dbe4f5", "#1b2440", 0.45]} />
      <directionalLight
        position={[-1.8, 3.2, 2.6]}
        intensity={1.7}
        color="#fff1e0"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-radius={5}
        shadow-bias={-0.0004}
        shadow-normalBias={0.02}
        shadow-camera-left={-1.6}
        shadow-camera-right={1.6}
        shadow-camera-top={2.4}
        shadow-camera-bottom={-0.4}
        shadow-camera-near={0.5}
        shadow-camera-far={9}
      />
      <directionalLight position={[2.6, 1.8, 2.2]} intensity={0.55} color="#a9c4ff" />
      <directionalLight position={[0.6, 2.6, -2.6]} intensity={1.0} color="#9fd9ff" />
    </>
  );
}

export default function AvatarViewer({ player, onKind }: { player: SequencePlayer; onKind?: (k: AvatarKind) => void }) {
  const [kind, setKind] = useState<AvatarKind | null>(null);
  const handleKind = useCallback(
    (k: AvatarKind) => {
      setKind(k);
      onKind?.(k);
    },
    [onKind],
  );
  if (typeof document !== "undefined" && !webglAvailable()) {
    return <Fallback message="WebGL is not available in this browser, so the 3D avatar cannot be shown. Sign glosses are still shown as text." />;
  }
  return (
    <SceneBoundary>
      <Canvas shadows dpr={[1, 1.75]} gl={{ alpha: true, antialias: true }} camera={{ position: [0, 1.3, 2.45], fov: 34 }} role="img" aria-label="3D signing avatar" style={{ background: "transparent" }}>
        {kind === "vrm" ? <AnimeLights /> : <StudioLights />}
        <Framing kind={kind} />
        <Suspense fallback={<Humanoid player={player} />}>
          <SignerAvatar player={player} onKind={handleKind} />
        </Suspense>
        <ContactShadows position={[0, 0.003, 0]} opacity={0.3} scale={4} blur={2.8} far={2.2} resolution={512} color="#4a1d4a" />
        <OrbitControls makeDefault target={[0, 1.25, 0]} enablePan={false} minDistance={1.3} maxDistance={5} maxPolarAngle={Math.PI * 0.52} />
      </Canvas>
    </SceneBoundary>
  );
}
