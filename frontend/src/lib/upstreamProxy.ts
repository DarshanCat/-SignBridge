/**
 * Server side helper of the same-origin routes /api/health and /api/model/status. They exist so that a deployment whose browser cannot call the API
 * directly (CORS, blocked ports) still gets the REAL answers of the real backend. They never answer on their own: when the backend is not
 * configured or does not answer, the route answers with an error, so the status panel shows what is true (backend unreachable, model unknown).
 */
export const PROXY_TIMEOUT_MS = 5000;

export type ProxyGetResult = { status: number; body: Record<string, unknown> };

export async function proxyGet(path: string, upstreamBase: string | undefined, fetchImpl: typeof fetch = fetch, timeoutMs: number = PROXY_TIMEOUT_MS): Promise<ProxyGetResult> {
  const base = (upstreamBase ?? "").trim().replace(/\/$/, "");
  if (!base) return { status: 503, body: { error: "no_upstream", detail: "No backend is configured (set SIGNBRIDGE_UPSTREAM_URL)." } };
  let res: Response;
  try {
    res = await fetchImpl(`${base}${path}`, { signal: AbortSignal.timeout(timeoutMs) });
  } catch {
    return { status: 502, body: { error: "upstream_unavailable", detail: "The backend could not be reached." } };
  }
  if (!res.ok) return { status: 502, body: { error: "upstream_error", detail: `The backend answered with HTTP ${res.status}.` } };
  try {
    const body = (await res.json()) as unknown;
    if (body && typeof body === "object" && !Array.isArray(body)) return { status: 200, body: body as Record<string, unknown> };
  } catch {
    /* fall through */
  }
  return { status: 502, body: { error: "upstream_invalid", detail: "The backend did not return a JSON object." } };
}
