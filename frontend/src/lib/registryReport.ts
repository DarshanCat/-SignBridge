/**
 * Registry status and avatar plan for the same-origin routes. They follow the Python backend (app/avatar/sign_registry.py, services/avatar_plan.py):
 * a clip counts only if its FILE exists, and a sign is `verified` only with a clip on disk and BOTH review flags. Nothing is assumed: an empty clips
 * folder means every registered asset is missing, not present.
 */
export interface RawSign {
  gloss: string;
  meaning?: string;
  asset_id?: string | null;
  license?: string | null;
  verification_status?: string;
  visually_reviewed?: boolean;
  signer_reviewed?: boolean;
}

export type SignStatus = "no_clip" | "clip_unreviewed" | "verified" | "missing_asset";

const clipName = (assetId: string) => assetId.toLowerCase().replace(/\.json$/i, "");

export function computeRegistry(signs: RawSign[], clipFiles: Iterable<string>) {
  const existing = new Set([...clipFiles].map((f) => clipName(f)));
  const used = new Set<string>();
  const out = signs.map((s) => {
    const gloss = (s.gloss || "").trim().toUpperCase();
    const problems: string[] = [];
    let status: SignStatus = "no_clip";
    if (s.asset_id) {
      const id = clipName(s.asset_id);
      used.add(id);
      if (!existing.has(id)) {
        status = "missing_asset";
        problems.push(`Asset ${s.asset_id} was not found on disk`);
      } else {
        status = s.visually_reviewed && s.signer_reviewed ? "verified" : "clip_unreviewed";
      }
    }
    if (s.verification_status === "verified" && status !== "verified") problems.push("registry claims verified but the evidence on disk does not support it");
    return {
      gloss,
      meaning: s.meaning || gloss.toLowerCase(),
      status,
      asset_id: s.asset_id ?? null,
      license: s.license ?? null,
      visually_reviewed: Boolean(s.visually_reviewed),
      signer_reviewed: Boolean(s.signer_reviewed),
      problems,
    };
  });
  const totals: Record<string, number> = { no_clip: 0, clip_unreviewed: 0, verified: 0, missing_asset: 0 };
  for (const s of out) totals[s.status] += 1;
  totals.signs = out.length;
  return { signs: out, unregistered_clips: [...existing].filter((c) => !used.has(c)).sort(), totals };
}

/** Which of the requested glosses have a clip file; a registered but absent asset is NOT available. */
export function planFromClips(glosses: string[], clipFiles: Iterable<string>) {
  const existing = new Set([...clipFiles].map((f) => clipName(f).toUpperCase()));
  const steps = glosses.map((g) => {
    const upper = g.toUpperCase();
    const available = existing.has(upper);
    return { gloss: upper, available, clip_url: available ? `/animations/${upper.toLowerCase()}.json` : null };
  });
  const missing = steps.filter((s) => !s.available).map((s) => s.gloss);
  const playable = steps.some((s) => s.available);
  const message = !playable
    ? "No animation clips are available for these signs, so nothing can be played."
    : missing.length === 0
      ? `All ${steps.length} sign(s) have animation clips.`
      : `${missing.length} of ${steps.length} sign(s) have no animation clip: ${missing.join(", ")}.`;
  return { steps, missing, playable, message };
}
