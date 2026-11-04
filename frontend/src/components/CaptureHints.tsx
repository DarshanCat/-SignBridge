"use client";
import { LOAD_PHASE_TEXT } from "@/lib/holistic";
import { resolutionLabel } from "@/lib/camera";
import { framingWarning, poseAdvice } from "@/lib/overlay";
import type { LandmarkCapture } from "./useLandmarkCapture";

/** What the landmark model is loading (with its step), and what the body pose tracker currently sees. */
export function CaptureHints({ capture }: { capture: LandmarkCapture }) {
  const { extractor, loadPhase, state, pose, resolution } = capture;
  const small = state === "running" ? framingWarning(pose) : null;
  return (
    <div aria-live="polite" className="mt-2 space-y-1 text-sm">
      {extractor === "loading" && (
        <p className="flex items-center gap-2 text-infofg">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-lav border-t-transparent" aria-hidden />
          {LOAD_PHASE_TEXT[loadPhase ?? "script"]}…
        </p>
      )}
      {extractor === "ready" && state !== "running" && <p className="text-goodfg">Landmark model ready.</p>}
      {state === "running" && resolution && (
        <p className="text-ink2">
          Camera: {resolutionLabel(resolution)}
          {resolution.width * 9 !== resolution.height * 16 ? " (not 16:9; recognition is most reliable at 16:9, so the picture is rescaled for the model)" : ""}
        </p>
      )}
      {small && <p role="alert" className="text-warnfg">{small}</p>}
      {state === "running" && <p className={pose.shoulders && pose.elbows ? "text-goodfg" : "text-warnfg"}>{poseAdvice(pose)}</p>}
    </div>
  );
}
