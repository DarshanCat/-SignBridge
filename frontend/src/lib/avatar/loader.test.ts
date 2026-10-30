import { describe, expect, it } from "vitest";
import { loadPlaylist } from "./loader";
import { RIG_TEST_CLIP } from "./rigTest";

const step = (gloss: string, available = true) => ({ gloss, available, clip_url: available ? `/animations/${gloss}.json` : null });
const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });

describe("loadPlaylist", () => {
  it("loads valid clips in order and skips unavailable steps", async () => {
    const r = await loadPlaylist([step("A"), step("B", false), step("C")], async () => ok(RIG_TEST_CLIP));
    expect(r.clips).toHaveLength(2);
    expect(r.failed).toEqual([]);
  });

  it("reports failed fetches and invalid clips without throwing", async () => {
    const fetcher = async (u: string) => (u.includes("A") ? { ok: false, status: 404, json: async () => ({}) } : u.includes("B") ? ok({ nope: 1 }) : ok(RIG_TEST_CLIP));
    const r = await loadPlaylist([step("A"), step("B"), step("C")], fetcher);
    expect(r.failed).toEqual(["A", "B"]);
    expect(r.clips).toHaveLength(1);
  });

  it("handles network errors", async () => {
    const r = await loadPlaylist([step("A")], async () => {
      throw new Error("offline");
    });
    expect(r.failed).toEqual(["A"]);
  });
});
