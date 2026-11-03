import { NextResponse } from "next/server";
import { listClipFiles } from "../../../../lib/clipFiles";
import { planFromClips } from "../../../../lib/registryReport";

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { gloss?: unknown };
    if (!Array.isArray(body.gloss) || !body.gloss.every((g) => typeof g === "string")) {
      return NextResponse.json({ detail: "gloss must be a list of strings." }, { status: 422 });
    }
    return NextResponse.json(planFromClips(body.gloss as string[], listClipFiles()));
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: msg }, { status: 400 });
  }
}
