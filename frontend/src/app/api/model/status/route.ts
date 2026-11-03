import { NextResponse } from "next/server";
import { proxyGet } from "../../../../lib/upstreamProxy";

/** The real backend's model status, or an error: this route never says "loaded" on its own. */
export async function GET() {
  const r = await proxyGet("/api/model/status", process.env.SIGNBRIDGE_UPSTREAM_URL ?? process.env.NEXT_PUBLIC_API_URL);
  return NextResponse.json(r.body, { status: r.status });
}
