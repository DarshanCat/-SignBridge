import { NextResponse } from "next/server";
import { recognizeViaUpstream } from "../../../../lib/recognizeProxy";

/**
 * HTTP fallback of the live recognizer (for browsers that cannot open the WebSocket). It only forwards the landmark frames to the real API and maps
 * the answer; it never produces a label itself. On any failure it answers with an error status and no label (see lib/recognizeProxy.ts).
 */
export async function POST(req: Request) {
  let frames: unknown;
  try {
    frames = ((await req.json()) as { frames?: unknown }).frames;
  } catch {
    return NextResponse.json({ error: "bad_request", detail: "The body must be JSON with a frames list." }, { status: 400 });
  }
  const upstream = process.env.SIGNBRIDGE_UPSTREAM_URL ?? process.env.NEXT_PUBLIC_API_URL;
  const r = await recognizeViaUpstream(frames, upstream);
  return NextResponse.json(r.body, { status: r.status });
}
