import type { AvatarPlan, TextToGloss } from "../api";
import type { SignClip } from "./clip";
import { loadPlaylist, type LoadedPlaylist } from "./loader";
import { describeTokens, glossesToPlan, playOrder, type TokenView } from "./sentence";

export interface TextToClips {
  gloss: TextToGloss;
  views: TokenView[];
  /** Clips in sentence order (a gloss used twice is played twice). Empty when nothing has a clip. */
  clips: SignClip[];
  failed: string[];
}

export interface PipelineDeps {
  textToGloss: (text: string) => Promise<TextToGloss>;
  plan: (glosses: string[]) => Promise<AvatarPlan>;
  load?: (steps: AvatarPlan["steps"]) => Promise<LoadedPlaylist>;
  onStage?: (stage: string) => void;
}

/** English text to the clips the avatar will play. Glosses without a clip are reported in `views`, never replaced by anything. */
export async function textToClips(text: string, deps: PipelineDeps): Promise<TextToClips> {
  deps.onStage?.("Converting text to gloss");
  const gloss = await deps.textToGloss(text);
  if (gloss.tokens.length === 0) return { gloss, views: [], clips: [], failed: [] };
  deps.onStage?.("Looking up sign clips");
  const plan = await deps.plan(glossesToPlan(gloss.tokens));
  deps.onStage?.(`Loading ${plan.steps.filter((s) => s.available).length} clip(s)`);
  const { clips, failed } = await (deps.load ?? loadPlaylist)(plan.steps);
  const byGloss = new Map(clips.map((c) => [c.gloss.toUpperCase(), c]));
  const views = describeTokens(gloss.tokens, new Set(byGloss.keys()));
  return { gloss, views, clips: playOrder(views).flatMap((g) => byGloss.get(g) ?? []), failed };
}
