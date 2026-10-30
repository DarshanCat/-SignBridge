import type { AnimationRegistry, ModelStatus } from "./api";

export type Level = "ok" | "warn" | "off" | "pending";
export interface StatusItem {
  id: string;
  label: string;
  level: Level;
  detail: string;
}

export interface StatusInput {
  backend: "checking" | "connected" | "unreachable";
  model: ModelStatus | null;
  animations: AnimationRegistry | null;
  webcam: "unknown" | "available" | "unavailable";
  extractor?: "not_loaded" | "loading" | "ready" | "error";
}

/** Derive honest status indicators; unimplemented features are never reported as ready. */
export function buildStatusItems(s: StatusInput): StatusItem[] {
  const backend: StatusItem =
    s.backend === "connected"
      ? { id: "backend", label: "Backend connected", level: "ok", detail: "FastAPI responded to /api/health." }
      : s.backend === "checking"
        ? { id: "backend", label: "Checking backend", level: "pending", detail: "Waiting for /api/health." }
        : { id: "backend", label: "Backend unreachable", level: "off", detail: "Start the FastAPI server (see README)." };

  const webcam: StatusItem =
    s.webcam === "available"
      ? {
          id: "webcam",
          label: "Webcam available",
          level: "ok",
          detail: "A video input device was detected. Permission is requested only when you start the camera.",
        }
      : s.webcam === "unavailable"
        ? { id: "webcam", label: "Webcam unavailable", level: "off", detail: "No video input detected or the browser does not support it." }
        : { id: "webcam", label: "Checking webcam", level: "pending", detail: "Enumerating devices." };

  const model: StatusItem = !s.model
    ? { id: "model", label: "Model status unknown", level: "off", detail: "Backend not reachable." }
    : s.model.loaded
      ? { id: "model", label: "Recognition model loaded", level: "ok", detail: s.model.message }
      : {
          id: "model",
          label: s.model.state === "not_trained" ? "Model not trained" : "Model error",
          level: "warn",
          detail: s.model.message,
        };

  const anim: StatusItem = !s.animations
    ? { id: "anim", label: "Animation status unknown", level: "off", detail: "Backend not reachable." }
    : s.animations.count > 0
      ? { id: "anim", label: `${s.animations.count} animation clip(s)`, level: "ok", detail: s.animations.message }
      : { id: "anim", label: "Animation unavailable", level: "warn", detail: s.animations.message };

  const ex = s.extractor ?? "not_loaded";
  const landmarks: StatusItem =
    ex === "ready"
      ? { id: "landmarks", label: "Landmark extraction ready", level: "ok", detail: "MediaPipe Holistic is loaded in this browser." }
      : ex === "loading"
        ? { id: "landmarks", label: "Loading landmark extraction", level: "pending", detail: "Loading MediaPipe Holistic." }
        : ex === "error"
          ? { id: "landmarks", label: "Landmark extraction failed", level: "off", detail: "MediaPipe could not be loaded. Run npm run setup:mediapipe." }
          : { id: "landmarks", label: "Landmark extraction not loaded", level: "warn", detail: "Loads when you start the camera." };
  return [backend, webcam, landmarks, model, anim];
}
