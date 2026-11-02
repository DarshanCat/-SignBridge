"use client";
import { LOAD_PHASE_TEXT } from "@/lib/holistic";
import { poseAdvice } from "@/lib/overlay";
import type { LandmarkCapture } from "./useLandmarkCapture";

/** What the landmark model is loading (with its step), and what the body pose tracker currently sees. */
export function CaptureHints({ capture }: { capture: LandmarkCapture }) {
  const { extractor, loadPhase, state, pose } = capture;
  return (
    <div aria-live="polite" className="mt-2 space-y-1 text-xs">
      {extractor === "loading" && (
        <p className="flex items-center gap-2 text-sky-300">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-sky-300 border-t-transparent" aria-hidden />
          {LOAD_PHASE_TEXT[loadPhase ?? "script"]}…
        </p>
      )}
      {extractor === "ready" && state !== "running" && <p className="text-emerald-300">Landmark model ready.</p>}
      {state === "running" && <p className={pose.shoulders && pose.elbows ? "text-emerald-300" : "text-amber-300"}>{poseAdvice(pose)}</p>}
    </div>
  );
}
