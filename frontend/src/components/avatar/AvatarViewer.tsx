"use client";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Component, useMemo, type ReactNode } from "react";
import { CanvasTexture, SRGBColorSpace } from "three";
import type { SequencePlayer } from "@/lib/avatar/player";
import { SignerAvatar, type AvatarKind } from "./GlbHumanoid";

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

/** Simple studio wall: one big plane with a soft radial gradient, lighter behind the signer so the silhouette reads. */
function Backdrop() {
  const texture = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = c.height = 512;
    const g = c.getContext("2d");
    if (g) {
      const grad = g.createRadialGradient(256, 230, 20, 256, 256, 330);
      grad.addColorStop(0, "#2b3a66");
      grad.addColorStop(0.55, "#18233f");
      grad.addColorStop(1, "#0b1122");
      g.fillStyle = grad;
      g.fillRect(0, 0, 512, 512);
    }
    const t = new CanvasTexture(c);
    t.colorSpace = SRGBColorSpace;
    return t;
  }, []);
  return (
    <mesh position={[0, 1.4, -2.6]}>
      <planeGeometry args={[14, 9]} />
      <meshBasicMaterial map={texture} fog={false} toneMapped={false} />
    </mesh>
  );
}

export default function AvatarViewer({ player, onKind }: { player: SequencePlayer; onKind?: (k: AvatarKind) => void }) {
  if (typeof document !== "undefined" && !webglAvailable()) {
    return <Fallback message="WebGL is not available in this browser, so the 3D avatar cannot be shown. Sign glosses are still shown as text." />;
  }
  return (
    <SceneBoundary>
      <Canvas shadows dpr={[1, 2]} camera={{ position: [0, 1.3, 2.45], fov: 34 }} aria-label="3D signing avatar">
        <color attach="background" args={["#0f1730"]} />
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
        <Backdrop />
        <SignerAvatar player={player} onKind={onKind} />
        <ContactShadows position={[0, 0.003, 0]} opacity={0.6} scale={4} blur={2.4} far={2.2} resolution={512} color="#02040b" />
        <OrbitControls target={[0, 1.25, 0]} enablePan={false} minDistance={1.3} maxDistance={5} maxPolarAngle={Math.PI * 0.52} />
      </Canvas>
    </SceneBoundary>
  );
}
