import fs from "node:fs";
import path from "node:path";

/** Clip file names (without .json) that really exist in public/animations; used by the same-origin avatar routes. */
export function listClipFiles(dir: string = path.join(process.cwd(), "public", "animations")): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(".json") && f !== "index.json").map((f) => f.replace(/\.json$/i, ""));
}
