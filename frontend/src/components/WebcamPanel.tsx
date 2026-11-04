"use client";
import { cameraBoxStyle, FramingGuide } from "./CameraFrame";
import { Camera, CameraOff, ScanSearch, ShieldCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { apiPost, type LandmarkSequenceResult } from "@/lib/api";
import { CaptureHints } from "./CaptureHints";
import { PredictionPanel, type Heard } from "./PredictionPanel";
import { AvatarStage, StageBadge, StageCaption } from "./ui/AvatarStage";
import { SequencePlayer } from "@/lib/avatar/player";
import type { AvatarKind } from "./avatar/GlbHumanoid";
import type { LandmarkCapture } from "./useLandmarkCapture";

type Check =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "done"; result: LandmarkSequenceResult }
  | { kind: "error"; message: string };

export function WebcamPanel({
  capture,
  backendUp,
}: {
  capture: LandmarkCapture;
  backendUp: boolean;
}) {
  const { state, extractor, error, stats, runId, videoRef, canvasRef, start, stop, getBuffer } = capture;
  // Results are tagged with the camera run that produced them and only shown for the current run, so stopping the
  // camera (or restarting it) discards old and late results without any state reset.
  const [checkState, setCheckState] = useState<{ runId: number; value: Check }>({ runId: -1, value: { kind: "idle" } });
  const running = state === "running";
  const idle = { kind: "idle" } as const;
  const check: Check = running && checkState.runId === runId ? checkState.value : idle;
  const inFlight = useRef(false); // at most one server request at a time (no duplicate inference)
  const [player] = useState(() => new SequencePlayer()); // idle: the avatar listens (breathes, blinks); it does not sign on this tab
  const [kind, setKind] = useState<AvatarKind | null>(null);
  const [heard, setHeard] = useState<Heard>({ sequence: [], english: null, signing: false });
  useEffect(() => () => player.dispose(), [player]);
  const busy = state === "starting";

  async function validate() {
    if (inFlight.current) return;
    inFlight.current = true;
    const mine = runId;
    setCheckState({ runId: mine, value: { kind: "busy" } });
    try {
      const result = await apiPost<LandmarkSequenceResult>("/api/landmarks/extract", { frames: getBuffer() });
      setCheckState({ runId: mine, value: { kind: "done", result } });
    } catch (e) {
      setCheckState({ runId: mine, value: { kind: "error", message: e instanceof Error ? e.message : "Validation failed." } });
    } finally {
      inFlight.current = false;
    }
  }

  const avatarLabel = kind === "vrm" ? "Avatar: anime (VRM)" : kind === "glb" ? "Avatar: Mixamo model" : kind === "procedural" ? "Avatar: built-in figure" : "Avatar: loading";
  const caption = !running ? (
    <StageCaption detail="Start the camera and sign. What the recognizer understands appears here; it can be wrong." />
  ) : heard.sequence.length === 0 ? (
    <StageCaption detail={heard.signing ? "Watching you sign…" : "Listening. Sign now, then lower your hands between signs."} />
  ) : (
    <StageCaption gloss={heard.sequence.join(" ")} sentence={heard.english ?? undefined} detail={heard.signing ? "Watching you sign…" : "Recognized by the model, not checked by a signer. It can be wrong."} />
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
    <section className="card" aria-label="Webcam and landmarks">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="card-title">ISL Sign to English</h2>
        <button
          onClick={running ? stop : start}
          disabled={busy}
          className="btn btn-primary"
        >
          {running ? <CameraOff size={16} aria-hidden /> : <Camera size={16} aria-hidden />}
          {busy ? "Starting…" : running ? "Stop camera" : "Start camera"}
        </button>
      </div>

      <div className="relative mx-auto mt-3 max-w-3xl overflow-hidden rounded-3xl border border-edge/50 bg-cam text-camfg" style={cameraBoxStyle(capture.resolution)}>
        <video ref={videoRef} playsInline muted className="h-full w-full object-cover" aria-label="Webcam preview" />
        <canvas ref={canvasRef} width={capture.resolution?.width ?? 640} height={capture.resolution?.height ?? 480} className="pointer-events-none absolute inset-0 h-full w-full" />
        <FramingGuide capture={capture} />
        {!running && (
          <p className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-camfg">
            {busy
              ? extractor === "loading"
                ? "Loading the landmark model…"
                : "Waiting for camera…"
              : "Camera is off. Video stays in your browser and is never recorded or uploaded."}
          </p>
        )}
      </div>

      <CaptureHints capture={capture} />

      {error && (
        <p role="alert" className="mt-3 notice notice-bad">
          {error}
        </p>
      )}

      <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-sm">
        {[
          ["Buffered frames", stats.frames],
          ["With body pose", stats.withPose],
          ["With hands", stats.withHands],
        ].map(([k, v]) => (
          <div key={k} className="rounded-2xl bg-surface2 p-2">
            <dd className="card-title">{v}</dd>
            <dt className="text-ink2">{k}</dt>
          </div>
        ))}
      </dl>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          onClick={validate}
          disabled={!running || !backendUp || stats.frames === 0 || check.kind === "busy"}
          className="btn btn-sm"
        >
          <ShieldCheck size={16} aria-hidden /> Validate landmarks on server
        </button>
        {!backendUp && <span className="text-sm text-warnfg">Backend unreachable.</span>}
      </div>

      <div aria-live="polite" className="mt-2 text-sm">
        {check.kind === "done" && (
          <p className={check.result.usable ? "text-goodfg" : "text-warnfg"}>
            {check.result.usable
              ? `Sequence usable: ${check.result.valid_frames}/${check.result.num_frames} valid frames, ${check.result.frames_with_hands} with hands (${check.result.feature_dim} features/frame).`
              : check.result.warnings.join(" ")}
          </p>
        )}
        {check.kind === "error" && <p className="text-badfg">{check.message}</p>}
      </div>

      <PredictionPanel running={running} runId={runId} bufferFrames={stats.frames} getBuffer={getBuffer} setFrameListener={capture.setFrameListener} onHeard={setHeard} />

    </section>
    <div className="lg:sticky lg:top-4 lg:self-start">
      <h3 className="eyebrow mb-3">Your signing partner</h3>
      <AvatarStage
        player={player}
        onKind={setKind}
        badges={
          <>
            <StageBadge>{avatarLabel}</StageBadge>
            <StageBadge tone="warn">Recognition can be wrong</StageBadge>
          </>
        }
        caption={caption}
      />
    </div>
    </div>
  );
}
