import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";
import signRegistry from "@/config/sign_registry.json";

interface RawSign {
  gloss: string;
  meaning: string;
  context?: string;
  reference_source?: string | null;
  asset_id?: string | null;
  license?: string | null;
  attribution?: string | null;
  verification_status?: string;
  visually_reviewed?: boolean;
  signer_reviewed?: boolean;
}

export async function GET() {
  try {
    const animDir = path.join(process.cwd(), "public", "animations");
    const existingClips = new Set<string>();

    if (fs.existsSync(animDir)) {
      const files = fs.readdirSync(animDir);
      for (const f of files) {
        if (f.endsWith(".json") && f !== "index.json") {
          existingClips.add(f.replace(/\.json$/i, "").toLowerCase());
        }
      }
    }

    const signsList = (signRegistry?.signs ?? []) as RawSign[];
    const usedAssets = new Set<string>();

    const signs = signsList.map((s) => {
      const gloss = (s.gloss || "").trim().toUpperCase();
      const assetId = s.asset_id ? s.asset_id.toLowerCase().replace(/\.json$/i, "") : null;
      const problems: string[] = [];
      let status: "no_clip" | "clip_unreviewed" | "verified" | "missing_asset" = "no_clip";

      if (assetId) {
        usedAssets.add(assetId);
        const hasFile = existingClips.size === 0 || existingClips.has(assetId);
        if (!hasFile) {
          status = "missing_asset";
          problems.push(`Asset ${s.asset_id} was not found on disk`);
        } else {
          status = "clip_unreviewed";
          if (s.visually_reviewed && s.signer_reviewed) {
            status = "verified";
          }
        }
      }

      return {
        gloss,
        meaning: s.meaning || gloss.toLowerCase(),
        status,
        asset_id: s.asset_id ?? null,
        license: s.license ?? null,
        visually_reviewed: Boolean(s.visually_reviewed),
        signer_reviewed: Boolean(s.signer_reviewed),
        problems,
      };
    });

    const totals: Record<string, number> = {
      no_clip: 0,
      clip_unreviewed: 0,
      verified: 0,
      missing_asset: 0,
    };

    for (const s of signs) {
      totals[s.status] = (totals[s.status] || 0) + 1;
    }
    totals.signs = signs.length;

    const unregistered_clips = Array.from(existingClips)
      .filter((c) => !usedAssets.has(c))
      .sort();

    return NextResponse.json({
      signs,
      unregistered_clips,
      totals,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: msg }, { status: 500 });
  }
}
