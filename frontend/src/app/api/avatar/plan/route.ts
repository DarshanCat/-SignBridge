import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { gloss?: string[] };
    const glosses = body.gloss ?? [];
    const animDir = path.join(process.cwd(), "public", "animations");
    const existing = new Set<string>();
    if (fs.existsSync(animDir)) {
      for (const file of fs.readdirSync(animDir)) {
        if (file.endsWith(".json")) {
          existing.add(file.replace(/\.json$/i, "").toUpperCase());
        }
      }
    }

    const steps = glosses.map((g) => {
      const upper = g.toUpperCase();
      const hasClip = existing.has(upper);
      return {
        gloss: upper,
        available: hasClip,
        clip_url: hasClip ? `/animations/${upper.toLowerCase()}.json` : null,
      };
    });

    const missing = steps.filter((s) => !s.available).map((s) => s.gloss);
    const playable = steps.some((s) => s.available);

    return NextResponse.json({
      steps,
      missing,
      playable,
      message: playable
        ? `Plan created with ${steps.length} steps (${missing.length} missing clips).`
        : "No clips available for the requested glosses.",
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: msg }, { status: 400 });
  }
}
