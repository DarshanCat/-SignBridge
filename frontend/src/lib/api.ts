export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
}

export interface ModelStatus {
  state: "not_trained" | "loaded" | "error";
  loaded: boolean;
  model_path: string;
  classes: number;
  message: string;
}

export interface AnimationRegistry {
  count: number;
  animations: { gloss: string; clip_url: string }[];
  message: string;
  invalid: string[];
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { signal });
  if (!res.ok) throw new Error(await errorMessage(res, path));
  return (await res.json()) as T;
}

async function errorMessage(res: Response, path: string): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* fall through to the generic message */
  }
  return `Request to ${path} failed (HTTP ${res.status})`;
}

export interface LandmarkSequenceResult {
  num_frames: number;
  feature_dim: number;
  valid_frames: number;
  frames_with_hands: number;
  usable: boolean;
  warnings: string[];
}

export async function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw new Error(await errorMessage(res, path));
  return (await res.json()) as T;
}

export interface WordResult {
  word: string;
  gloss: string[];
  status: "mapped" | "dropped" | "unsupported";
}
export interface EnglishToGloss {
  gloss: string[];
  words: WordResult[];
  unsupported: string[];
  coverage: number;
  note: string;
}
export interface NlpGlossToken {
  gloss: string;
  kind: string;
  source: string;
  letters?: string[] | null;
}
export interface TextToGloss {
  gloss: string[];
  tokens: NlpGlossToken[];
  nmm: string[];
  tense: string;
  dropped: Record<string, unknown>[];
  fingerspelled: string[];
  note: string;
}
export interface PlanStep {
  gloss: string;
  available: boolean;
  clip_url: string | null;
}
export interface AvatarPlan {
  steps: PlanStep[];
  missing: string[];
  playable: boolean;
  message: string;
}
export interface Vocabulary {
  items: { gloss: string; english: string; has_animation: boolean }[];
  animated: number;
  note: string;
}

export interface SignTranslation {
  predictions: { label: string; confidence: number }[];
  num_frames_used: number;
  accepted: boolean;
  min_confidence: number;
  gloss: string[];
  english: string;
  unsupported: string[];
  message: string;
}

export interface SignStatus {
  gloss: string;
  meaning: string;
  status: "no_clip" | "clip_unreviewed" | "verified" | "missing_asset";
  asset_id: string | null;
  license: string | null;
  visually_reviewed: boolean;
  signer_reviewed: boolean;
  problems: string[];
}
export interface SignRegistry {
  signs: SignStatus[];
  unregistered_clips: string[];
  totals: Record<string, number>;
}

export interface RecordResult {
  accepted: boolean;
  gloss: string;
  signer_id?: string | null;
  reasons: string[];
  stats: { frames: number; no_pose_frames: number; no_hand_frames: number; fps: number; seconds: number; segments?: number };
  saved: boolean;
  feature_file: string | null;
  clip_file: string | null;
  clip: unknown;
  note: string;
}

export interface RecordPlan {
  glosses: string[];
  priority: string[];
  note: string;
}

export interface RecordTakes {
  signer_id: string;
  counts: Record<string, number>;
  total: number;
}
