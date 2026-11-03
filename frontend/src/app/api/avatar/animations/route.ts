import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";
import signRegistry from "@/config/sign_registry.json";

export async function GET() {
  try {
    const animDir = path.join(process.cwd(), "public", "animations");
    const map = new Map<string, string>();

    if (fs.existsSync(animDir)) {
      const files = fs.readdirSync(animDir).filter((f) => f.endsWith(".json"));
      for (const file of files) {
        const gloss = file.replace(/\.json$/i, "").toUpperCase();
        map.set(gloss, `/animations/${file}`);
      }
    }

    if (Array.isArray(signRegistry?.signs)) {
      for (const s of signRegistry.signs) {
        if (s.asset_id && s.gloss && !map.has(s.gloss.toUpperCase())) {
          map.set(s.gloss.toUpperCase(), `/animations/${s.asset_id}`);
        }
      }
    }

    const animations = Array.from(map.entries()).map(([gloss, clip_url]) => ({
      gloss,
      clip_url,
    }));

    return NextResponse.json({
      count: animations.length,
      animations,
      message: `${animations.length} animation clip(s) available.`,
      invalid: [],
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { count: 0, animations: [], message: `Failed to load animations: ${msg}`, invalid: [] },
      { status: 500 }
    );
  }
}
