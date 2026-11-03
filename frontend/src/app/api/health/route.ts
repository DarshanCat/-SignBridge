import { NextResponse } from "next/server";
import { proxyGet } from "../../../lib/upstreamProxy";

/** The real backend's answer, or an error: this route never says "ok" on its own. */
export async function GET() {
  const r = await proxyGet("/api/health", process.env.SIGNBRIDGE_UPSTREAM_URL ?? process.env.NEXT_PUBLIC_API_URL);
  return NextResponse.json(r.body, { status: r.status });
}
