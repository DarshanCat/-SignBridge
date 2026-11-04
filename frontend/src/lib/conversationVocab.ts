import { describeTokens, type GlossTokenIn } from "./avatar/sentence";

export interface VocabItem {
  gloss: string;
  group: string;
  include_class: string | null;
  must_record: boolean;
  note: string;
}
export interface ConversationVocabulary {
  signs: VocabItem[];
  known: number;
  to_record: number;
  test_sentences: string[];
}
export interface KnownSign {
  gloss: string;
  label: string;
}
export interface KnownSigns {
  loaded: boolean;
  count: number;
  signs: KnownSign[];
  note: string;
}

/** Case insensitive search over the sign name and its gloss; hyphens and spaces count the same ("thank you" finds THANK-YOU). */
export function filterSigns(signs: KnownSign[], query: string): KnownSign[] {
  const q = query.trim().toLowerCase().replace(/[-\s]+/g, " ");
  if (!q) return signs;
  return signs.filter((s) => `${s.label} ${s.gloss}`.toLowerCase().replace(/[-\s]+/g, " ").includes(q));
}

export interface SentenceRow {
  text: string;
  gloss: string;
  /** Tokens that cannot be shown, with whether they are signs of the conversation vocabulary that still have to be recorded. */
  missing: { gloss: string; toRecord: boolean }[];
  nmm: string[];
}

/** "FS:DO" is the fingerspelled form of the word DO: for the vocabulary it is the sign DO that is missing. */
const baseGloss = (g: string): string => g.replace(/^FS:/, "");

/** The gloss of a test sentence and which of its signs are missing (no clip). `available` are the glosses that have a clip. */
export function sentenceRow(
  text: string,
  gloss: { gloss: string[]; tokens: GlossTokenIn[]; nmm: string[] },
  available: ReadonlySet<string>,
  vocab: ConversationVocabulary | null,
): SentenceRow {
  const toRecord = new Set((vocab?.signs ?? []).filter((s) => s.must_record).map((s) => s.gloss));
  const missing = describeTokens(gloss.tokens, available)
    .filter((v) => v.status === "no_clip")
    .map((v) => ({ gloss: v.gloss, toRecord: toRecord.has(baseGloss(v.gloss)) }));
  return { text, gloss: gloss.gloss.join(" "), missing, nmm: gloss.nmm };
}
