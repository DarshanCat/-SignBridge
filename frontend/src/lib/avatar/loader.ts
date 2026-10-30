import type { PlanStep } from "../api";
import { parseClip, type SignClip } from "./clip";

export interface LoadedPlaylist {
  clips: SignClip[];
  /** Glosses whose clip was announced by the backend but could not be fetched or validated. */
  failed: string[];
}

type Fetcher = (url: string) => Promise<{ ok: boolean; status: number; json(): Promise<unknown> }>;

/** Fetch and validate the clips (served by the frontend at /animations) for every available step, in order. Never throws for a bad clip. */
export async function loadPlaylist(steps: PlanStep[], fetcher: Fetcher = (u) => fetch(u)): Promise<LoadedPlaylist> {
  const clips: SignClip[] = [];
  const failed: string[] = [];
  for (const step of steps) {
    if (!step.available || !step.clip_url) continue;
    try {
      const res = await fetcher(step.clip_url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      clips.push(parseClip(await res.json()));
    } catch {
      failed.push(step.gloss);
    }
  }
  return { clips, failed };
}
