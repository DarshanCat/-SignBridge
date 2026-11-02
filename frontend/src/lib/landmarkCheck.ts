import { REFERENCE_ASPECT, type LandmarkFrame } from "./landmarks";

/** Formats tried for the local video recording, best first. */
export const VIDEO_MIME_CANDIDATES = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm", "video/mp4"];

export function pickMimeType(isSupported: (m: string) => boolean): string | null {
  return VIDEO_MIME_CANDIDATES.find(isSupported) ?? null;
}

export const extensionFor = (mime: string): string => (mime.startsWith("video/mp4") ? "mp4" : "webm");

/** File name stem shared by the video and the landmark file, for example signbridge_check_20261031_101502. */
export function fileStem(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `signbridge_check_${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

export interface TimedFrame extends LandmarkFrame {
  /** Milliseconds from the start of the video recording to the moment this frame's landmarks were produced. */
  t: number;
}

export interface CheckFile {
  version: 1;
  created: string;
  video_file: string;
  video_mime: string;
  video_duration_ms: number;
  extractor: { delegate: "cpu" | "gpu"; model_complexity: 0 };
  /** Frames already have y rescaled to this aspect (see toFrame); video_aspect is the recorded video's own width / height. */
  reference_aspect: number;
  video_aspect: number | null;
  frames: TimedFrame[];
}

/** Landmark file for the Python comparison. Frames before the video started or after it ended are dropped. */
export function buildCheckFile(
  stem: string, mime: string, durationMs: number, frames: LandmarkFrame[], times: number[], startMs: number, cpu: boolean, now: Date, videoAspect: number | null = null,
): CheckFile {
  const out: TimedFrame[] = [];
  frames.forEach((f, i) => {
    const t = times[i] - startMs;
    if (t >= 0 && t <= durationMs) out.push({ ...f, t: Math.round(t * 10) / 10 });
  });
  return {
    version: 1,
    created: now.toISOString(),
    video_file: `${stem}.${extensionFor(mime)}`,
    video_mime: mime,
    video_duration_ms: Math.round(durationMs),
    extractor: { delegate: cpu ? "cpu" : "gpu", model_complexity: 0 },
    reference_aspect: REFERENCE_ASPECT,
    video_aspect: videoAspect,
    frames: out,
  };
}

/** The command that compares the two downloaded files (run from the backend folder). */
export function compareCommand(stem: string, mime: string): string {
  return `.\\.venv\\Scripts\\python -m training.compare_landmarks --video "$HOME\\Downloads\\${stem}.${extensionFor(mime)}" --landmarks "$HOME\\Downloads\\${stem}.landmarks.json"`;
}
