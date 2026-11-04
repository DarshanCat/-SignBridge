import { describe, expect, it } from "vitest";
import { filterSigns, sentenceRow, type ConversationVocabulary } from "./conversationVocab";

const vocab: ConversationVocabulary = {
  signs: [
    { gloss: "DO", group: "verb", include_class: null, must_record: true, note: "" },
    { gloss: "WHAT", group: "question", include_class: null, must_record: true, note: "" },
    { gloss: "YOU", group: "pronoun", include_class: "you", must_record: false, note: "" },
  ],
  known: 1,
  to_record: 2,
  test_sentences: [],
};

describe("filterSigns", () => {
  const signs = [
    { gloss: "THANK-YOU", label: "Thank you" },
    { gloss: "HELLO", label: "Hello" },
    { gloss: "STORE-OR-SHOP", label: "Store or Shop" },
  ];
  it("returns everything for an empty query", () => expect(filterSigns(signs, "  ")).toHaveLength(3));
  it("matches the label and the gloss, ignoring case, hyphens and spaces", () => {
    expect(filterSigns(signs, "thank you").map((s) => s.gloss)).toEqual(["THANK-YOU"]);
    expect(filterSigns(signs, "THANK-").map((s) => s.gloss)).toEqual(["THANK-YOU"]);
    expect(filterSigns(signs, "shop")).toHaveLength(1);
    expect(filterSigns(signs, "zzz")).toHaveLength(0);
  });
});

describe("sentenceRow", () => {
  const gloss = {
    gloss: ["YOU", "FS:DO", "WHAT"],
    nmm: ["wh-question"],
    tokens: [
      { gloss: "YOU", kind: "sign" },
      { gloss: "FS:DO", kind: "fingerspell", letters: ["D", "O"] },
      { gloss: "WHAT", kind: "sign" },
    ],
  };
  it("lists the tokens without a clip and marks the vocabulary signs still to record", () => {
    const r = sentenceRow("What are you doing?", gloss, new Set(["YOU"]), vocab);
    expect(r.gloss).toBe("YOU FS:DO WHAT");
    expect(r.missing).toEqual([{ gloss: "FS:DO", toRecord: true }, { gloss: "WHAT", toRecord: true }]);
  });
  it("lists nothing when every sign has a clip, and works without the vocabulary", () => {
    expect(sentenceRow("x", gloss, new Set(["YOU", "WHAT", "FS-D", "FS-O"]), vocab).missing).toEqual([]);
    expect(sentenceRow("x", gloss, new Set(["YOU"]), null).missing.every((m) => !m.toRecord)).toBe(true);
  });
});
