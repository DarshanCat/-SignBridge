// Fetch the avatar model and the sign clips from a PRIVATE Hugging Face repository into public/ at build time, so they are served by the
// deployment but never committed to the (public) git repository.
//   SIGNBRIDGE_ASSETS_REPO   repository id, for example your-name/signbridge-assets (unset: skip)
//   SIGNBRIDGE_ASSETS_TYPE   dataset (default) or model
//   HF_TOKEN                 read token (a Vercel environment variable, build time only, never NEXT_PUBLIC_)
// Expected layout of the repository: animations/*.json and avatar/signer.glb
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repo = (process.env.SIGNBRIDGE_ASSETS_REPO ?? "").trim();
if (!repo) {
  console.log("fetch-assets: SIGNBRIDGE_ASSETS_REPO is not set, skipping. Without clips the English to Sign tab has nothing to sign; without the GLB the built-in figure is used.");
  process.exit(0);
}
const type = (process.env.SIGNBRIDGE_ASSETS_TYPE ?? "dataset").trim() === "model" ? "model" : "dataset";
const token = process.env.HF_TOKEN;
const headers = token ? { Authorization: `Bearer ${token}` } : {};
const pub = join(dirname(fileURLToPath(import.meta.url)), "..", "public");
const apiBase = `https://huggingface.co/api/${type}s/${repo}`;
const fileBase = `https://huggingface.co/${type === "dataset" ? "datasets/" : ""}${repo}/resolve/main`;

async function get(url) {
  const res = await fetch(url, { headers, redirect: "follow" });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url.replace(fileBase, "<repo>")}`);
  return res;
}

async function main() {
  const list = await (await get(`${apiBase}/tree/main/animations`)).json();
  const clips = list.filter((e) => e.type === "file" && e.path.endsWith(".json")).map((e) => e.path);
  const wanted = [...clips, "avatar/signer.glb"];
  let done = 0;
  const queue = [...wanted];
  async function worker() {
    for (let p = queue.shift(); p; p = queue.shift()) {
      const body = Buffer.from(await (await get(`${fileBase}/${p}`)).arrayBuffer());
      const dest = join(pub, p);
      await mkdir(dirname(dest), { recursive: true });
      await writeFile(dest, body);
      done++;
    }
  }
  await Promise.all(Array.from({ length: 8 }, worker));
  console.log(`fetch-assets: ${clips.length} clips and the avatar model written to public/ (${done} files)`);
}

main().catch((e) => {
  // never print the token; the message only names the failing path
  console.error(`fetch-assets: failed: ${e.message}`);
  process.exit(1);
});
