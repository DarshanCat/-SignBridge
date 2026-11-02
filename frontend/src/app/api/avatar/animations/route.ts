import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

export async function GET() {
  try {
    const animDir = path.join(process.cwd(), "public", "animations");
    if (!fs.existsSync(animDir)) {
      return NextResponse.json({
        count: 0,
        animations: [],
        message: "No sign animation clips available yet.",
        invalid: [],
      });
    }

    const files = fs.readdirSync(animDir).filter((f) => f.endsWith(".json"));
    const animations = files.map((file) => {
      const gloss = file.replace(/\.json$/i, "").toUpperCase();
      return {
        gloss,
        clip_url: `/animations/${file}`,
      };
    });

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
