/** Turn a getUserMedia failure into a safe, actionable message. */
export function cameraErrorMessage(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  switch (name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Camera permission was denied. Allow camera access in your browser's site settings and try again.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "No camera was found. Connect a webcam and try again.";
    case "NotReadableError":
    case "AbortError":
      return "The camera is in use by another application or could not be started.";
    default:
      if (err instanceof TypeError && typeof navigator !== "undefined" && !navigator.mediaDevices?.getUserMedia) {
        return "This browser cannot access the camera (HTTPS or localhost is required).";
      }
      return err instanceof Error ? err.message : "The camera could not be started.";
  }
}

export interface Resolution {
  width: number;
  height: number;
}

/** Asked for first: 16:9, the shape the model was trained on (see docs/evaluation/BROWSER_PATH.md). The camera may give something else. */
export const PREFERRED_RESOLUTION: Resolution = { width: 1280, height: 720 };

/** Constraint sets tried in order: the preferred size (ideal, so the closest the camera has is used), then whatever the camera gives. */
export function cameraConstraintSets(preferred: Resolution = PREFERRED_RESOLUTION): MediaStreamConstraints[] {
  return [
    { video: { width: { ideal: preferred.width }, height: { ideal: preferred.height }, facingMode: "user" }, audio: false },
    { video: true, audio: false },
  ];
}

/** Permission problems end the search at once; anything else (overconstrained, odd driver) moves on to the next constraint set. */
export async function openCamera(
  getUserMedia: (c: MediaStreamConstraints) => Promise<MediaStream>,
  sets: MediaStreamConstraints[] = cameraConstraintSets(),
): Promise<MediaStream> {
  let last: unknown = new Error("No camera constraints to try.");
  for (const c of sets) {
    try {
      return await getUserMedia(c);
    } catch (e) {
      last = e;
      const name = e instanceof DOMException ? e.name : "";
      if (name === "NotAllowedError" || name === "SecurityError" || name === "NotReadableError") break;
    }
  }
  throw last;
}

export const resolutionLabel = (r: Resolution): string => `${r.width} x ${r.height}`;

/** Aspect of a camera picture as the landmark conversion needs it, with a safe default before the size is known. */
export const aspectOf = (r: Resolution | null): number => (r && r.width > 0 && r.height > 0 ? r.width / r.height : 4 / 3);
