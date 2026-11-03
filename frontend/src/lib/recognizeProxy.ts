/**
 * Server side helper of the HTTP fallback route /api/signs/recognize (used when a browser cannot open the WebSocket).
 *
 * Rule of this project: a prediction comes from the trained model or it does not exist. This helper forwards the landmark frames to the real
 * API (POST /api/signs/translate) and maps the answer. When the call fails for any reason (no upstream configured, network error, timeout,
 * non-success status, an answer that is not a recognition result) it returns an error and NEVER a label, a confidence or alternatives.
 */

/** The validated live threshold of the 1D CNN (docs/evaluation/results.md); the upstream default is lower, so it is applied here again. */
export const LIVE_THRESHOLD = 0.7;
export const UPSTREAM_TIMEOUT_MS = 8000;

export type ProxyResult =
  | { ok: true; status: 200; body: Record<string, unknown> }
  | { ok: false; status: number; body: { error: string; detail: string } };

interface Upstream {
  predictions?: { label?: unknown; confidence?: unknown }[];
  num_frames_used?: unknown;
  gloss?: unknown;
  english?: unknown;
}

const fail = (status: number, error: string, detail: string): ProxyResult => ({ ok: false, status, body: { error, detail } });

function hasHand(f: unknown): boolean {
  const x = f as { left_hand?: unknown; right_hand?: unknown } | null;
  return !!x && ((Array.isArray(x.left_hand) && x.left_hand.length > 0) || (Array.isArray(x.right_hand) && x.right_hand.length > 0));
}

export async function recognizeViaUpstream(
  frames: unknown,
  upstreamBase: string | undefined,
  fetchImpl: typeof fetch = fetch,
  timeoutMs: number = UPSTREAM_TIMEOUT_MS,
): Promise<ProxyResult> {
  if (!Array.isArray(frames) || frames.length === 0) return fail(400, "bad_frames", "frames must be a non-empty list of landmark frames.");
  if (!frames.some(hasHand)) {
    // not a prediction: no sign was attempted, so nothing is classified and no confidence or alternative is reported
    return { ok: true, status: 200, body: { type: "prediction", accepted: false, label: "UNRECOGNIZED", gloss: null, reason: "no_hands", message: "No hands detected in the frames. Raise your hands into camera view to sign." } };
  }
  const base = (upstreamBase ?? "").trim().replace(/\/$/, "");
  if (!base) return fail(503, "no_upstream", "No recognition backend is configured for this route (set SIGNBRIDGE_UPSTREAM_URL).");
  let res: Response;
  try {
    res = await fetchImpl(`${base}/api/signs/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frames }),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch {
    return fail(502, "upstream_unavailable", "The recognition backend could not be reached.");
  }
  if (!res.ok) return fail(502, "upstream_error", `The recognition backend answered with HTTP ${res.status}.`);
  let data: Upstream;
  try {
    data = (await res.json()) as Upstream;
  } catch {
    return fail(502, "upstream_invalid", "The recognition backend did not return JSON.");
  }
  const preds = Array.isArray(data.predictions) ? data.predictions : [];
  const top = preds[0];
  if (!top || typeof top.label !== "string" || typeof top.confidence !== "number" || !Number.isFinite(top.confidence)) {
    return fail(502, "upstream_invalid", "The recognition backend returned no usable prediction.");
  }
  const accepted = top.confidence >= LIVE_THRESHOLD;
  const gloss = accepted && Array.isArray(data.gloss) && typeof data.gloss[0] === "string" ? (data.gloss[0] as string) : null;
  return {
    ok: true,
    status: 200,
    body: {
      type: "prediction",
      accepted,
      label: accepted ? top.label : "UNRECOGNIZED",
      gloss,
      confidence: top.confidence,
      threshold: LIVE_THRESHOLD,
      threshold_source: "validation",
      alternatives: preds.filter((p) => typeof p.label === "string" && typeof p.confidence === "number"),
      num_frames_used: typeof data.num_frames_used === "number" ? data.num_frames_used : frames.length,
      sequence: gloss ? [gloss] : [],
      english: accepted && typeof data.english === "string" ? data.english : "",
    },
  };
}
