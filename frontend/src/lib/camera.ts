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
