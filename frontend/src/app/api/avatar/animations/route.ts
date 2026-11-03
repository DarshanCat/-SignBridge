import { NextResponse } from "next/server";
import { listClipFiles } from "../../../../lib/clipFiles";

/** The clips that exist as files in public/animations; a registered asset without a file is not listed. */
export async function GET() {
  try {
    const animations = listClipFiles()
      .map((name) => ({ gloss: name.toUpperCase(), clip_url: `/animations/${name}.json` }))
      .sort((a, b) => a.gloss.localeCompare(b.gloss));
    return NextResponse.json({ count: animations.length, animations, message: `${animations.length} animation clip(s) available.`, invalid: [] });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: `Failed to list the animation clips: ${msg}` }, { status: 500 });
  }
}
