"use client";
import type { CSSProperties } from "react";
import { aspectOf, type Resolution } from "@/lib/camera";
import type { LandmarkCapture } from "./useLandmarkCapture";

/** The picture box follows the camera's real aspect ratio, so nothing is cropped and the landmark overlay lines up with the video. */
export function cameraBoxStyle(resolution: Resolution | null): CSSProperties {
  return { aspectRatio: String(aspectOf(resolution)) };
}

/**
 * Dashed outline of where the head, shoulders and hands should be: shoulders about 14 percent of the picture width, hands raised in front of the
 * chest, all inside the picture. This sits inside the range that was tested (INCLUDE signers measure 12 to 15 percent, accuracy was measured up to
 * 17 percent, docs/evaluation/BROWSER_PATH.md). Larger sizes are NOT recommended: cropping toward the signer cut the hands out of the picture
 * (a hand was found in only 33 to 63 percent of frames) and accuracy fell, so sizes above 0.15 are untested. Drawn only while the camera runs; it is a
 * guide, not a measurement.
 */
export function FramingGuide({ capture }: { capture: LandmarkCapture }) {
  if (capture.state !== "running") return null;
  const stroke = { fill: "none", stroke: "rgba(255,255,255,0.45)", strokeWidth: 1.2, strokeDasharray: "3 3", vectorEffect: "non-scaling-stroke" } as const;
  return (
    <svg aria-hidden viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
      <ellipse cx="50" cy="26" rx="2.6" ry="7" {...stroke} />
      <path d="M 43 38 Q 50 34 57 38 L 58 100 M 43 38 L 42 100" {...stroke} />
      <rect x="28" y="42" width="13" height="32" rx="5" {...stroke} />
      <rect x="59" y="42" width="13" height="32" rx="5" {...stroke} />
    </svg>
  );
}
