import type { LandmarkFrame } from "./landmarks";

export const COUNTDOWN_FROM = 3;
export const DURATIONS_S = [2, 3, 4, 5] as const;
export const GLOSS_PATTERN = /^[A-Z0-9][A-Z0-9-]{0,31}$/;

/** Same normalisation as the backend: trim, upper case, spaces and underscores become hyphens. */
export function normalizeGloss(raw: string): string {
  return raw.trim().toUpperCase().replace(/[_\s]+/g, "-");
}

export const isValidGloss = (raw: string): boolean => GLOSS_PATTERN.test(normalizeGloss(raw));

/** Frames per second actually achieved during the take (the extractor runs slower than the camera on weak machines). */
export function measureFps(frameCount: number, elapsedMs: number): number {
  if (frameCount <= 0 || elapsedMs <= 0) return 0;
  return Math.round((frameCount / (elapsedMs / 1000)) * 100) / 100;
}

export interface RecordRequestBody {
  gloss: string;
  fps: number;
  frames: LandmarkFrame[];
}

/** Request body for POST /api/record/sign. Landmarks only: there is no video in it. */
export function buildRecordRequest(gloss: string, frames: LandmarkFrame[], elapsedMs: number): RecordRequestBody {
  return { gloss: normalizeGloss(gloss), fps: measureFps(frames.length, elapsedMs), frames };
}

/** Countdown labels 3, 2, 1 shown one per second before recording starts. */
export const countdownSteps = (from: number = COUNTDOWN_FROM): number[] => Array.from({ length: from }, (_, i) => from - i);
