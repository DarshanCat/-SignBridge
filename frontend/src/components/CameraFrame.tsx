"use client";
import type { CSSProperties } from "react";
import { aspectOf, type Resolution } from "@/lib/camera";
import type { LandmarkCapture } from "./useLandmarkCapture";

/** The picture box follows the camera's real aspect ratio, so nothing is cropped and the landmark overlay lines up with the video. */
export function cameraBoxStyle(resolution: Resolution | null): CSSProperties {
  return { aspectRatio: String(aspectOf(resolution)) };
}

/**
 * Dashed outline of where the head, shoulders and hands should be: shoulders about 22 percent of the picture width (INCLUDE signers are 12 to 15 percent, a webcam signer who fills the frame is larger; larger sizes are not measured), hands raised in front of
 * the chest. Drawn only while the camera runs; it is a guide, not a measurement.
 */
export function FramingGuide({ capture }: { capture: LandmarkCapture }) {
  if (capture.state !== "running") return null;
  const stroke = { fill: "none", stroke: "rgba(255,255,255,0.45)", strokeWidth: 1.2, strokeDasharray: "3 3", vectorEffect: "non-scaling-stroke" } as const;
  return (
    <svg aria-hidden viewBox="0 0 100 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
      <ellipse cx="50" cy="26" rx="6.5" ry="11" {...stroke} />
      <path d="M 39 45 Q 50 38 61 45 L 63 100 M 39 45 L 37 100" {...stroke} />
      <rect x="16" y="52" width="18" height="30" rx="8" {...stroke} />
      <rect x="66" y="52" width="18" height="30" rx="8" {...stroke} />
    </svg>
  );
}
