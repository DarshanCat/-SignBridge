// Copies the MediaPipe Holistic runtime (Apache-2.0, from the npm package) into public/ so the
// browser loads it from this site instead of a CDN. Output is git-ignored.
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "node_modules", "@mediapipe", "holistic");
const dest = join(root, "public", "mediapipe", "holistic");

if (!existsSync(src)) {
  console.error("@mediapipe/holistic is not installed; run npm install first.");
  process.exit(1);
}
mkdirSync(dest, { recursive: true });
const files = [
  "holistic.js",
  "holistic.binarypb",
  "holistic_solution_packed_assets.data",
  "holistic_solution_packed_assets_loader.js",
  "holistic_solution_simd_wasm_bin.data",
  "holistic_solution_simd_wasm_bin.js",
  "holistic_solution_simd_wasm_bin.wasm",
  "holistic_solution_wasm_bin.js",
  "holistic_solution_wasm_bin.wasm",
  "pose_landmark_lite.tflite",
  "pose_landmark_full.tflite",
];
for (const f of files) cpSync(join(src, f), join(dest, f));
console.log(`Copied ${files.length} MediaPipe Holistic files to public/mediapipe/holistic`);
