import { NextResponse } from "next/server";
import glossDictionary from "@/config/gloss_dictionary.json";
import translationCfg from "@/config/translation.json";

interface TokenOut {
  gloss: string;
  kind: "sign" | "fingerspell";
  source: string;
  letters?: string[] | null;
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { text?: string };
    const text = (body.text ?? "").trim();
    if (!text) {
      return NextResponse.json({
        gloss: [],
        tokens: [],
        nmm: [],
        tense: "present",
        dropped: [],
        fingerspelled: [],
        note: "Empty text",
      });
    }

    const stopwords = new Set(translationCfg.stopwords || []);
    const pronouns = glossDictionary.pronoun_forms as Record<string, string>;
    const signs = glossDictionary.signs as Record<string, { words: string[]; pos?: string }>;

    // Build word to gloss map
    const wordMap = new Map<string, string>();
    for (const [gloss, info] of Object.entries(signs)) {
      wordMap.set(gloss.toLowerCase(), gloss);
      if (Array.isArray(info.words)) {
        for (const w of info.words) {
          wordMap.set(w.toLowerCase(), gloss);
        }
      }
    }
    // Also include custom translation dictionary entries
    if (translationCfg.glosses) {
      for (const [gloss, info] of Object.entries(translationCfg.glosses as Record<string, { words: string[] }>)) {
        wordMap.set(gloss.toLowerCase(), gloss);
        for (const w of info.words || []) {
          wordMap.set(w.toLowerCase(), gloss);
        }
      }
    }

    // Tokenize
    const rawWords = text.match(/[A-Za-z']+/g) || [];
    const tokens: TokenOut[] = [];
    const dropped: Record<string, unknown>[] = [];
    const fingerspelled: string[] = [];

    // Check phrases first
    const phrases = translationCfg.english_phrases || [];
    const lowerTokens = rawWords.map((w) => w.toLowerCase());
    let i = 0;

    while (i < lowerTokens.length) {
      let matched = false;
      for (const phrase of phrases) {
        const pWords = phrase.words.map((w: string) => w.toLowerCase());
        if (i + pWords.length <= lowerTokens.length) {
          const slice = lowerTokens.slice(i, i + pWords.length);
          if (slice.join(" ") === pWords.join(" ")) {
            for (const g of phrase.gloss) {
              tokens.push({
                gloss: g,
                kind: "sign",
                source: slice.join(" "),
              });
            }
            i += pWords.length;
            matched = true;
            break;
          }
        }
      }
      if (matched) continue;

      const w = lowerTokens[i];
      const orig = rawWords[i];

      if (pronouns[w]) {
        tokens.push({ gloss: pronouns[w], kind: "sign", source: orig });
      } else if (wordMap.has(w)) {
        tokens.push({ gloss: wordMap.get(w)!, kind: "sign", source: orig });
      } else if (stopwords.has(w)) {
        dropped.push({ word: orig, reason: "stopword" });
      } else {
        const fsGloss = `FS(${orig.toUpperCase()})`;
        tokens.push({
          gloss: fsGloss,
          kind: "fingerspell",
          source: orig,
          letters: orig.toUpperCase().split(""),
        });
        fingerspelled.push(orig);
      }
      i++;
    }

    // Question & NMM detection
    const nmm: string[] = [];
    const isQuestion = text.endsWith("?") || lowerTokens.some((w) => ["what", "where", "who", "when", "why", "how"].includes(w));
    if (isQuestion) {
      nmm.push("wh-question");
    }
    const hasNegation = lowerTokens.some((w) => ["not", "no", "never", "don't", "cant", "cannot"].includes(w));
    if (hasNegation) {
      nmm.push("negation");
    }

    // Question words to end (ISL SOV grammar rule)
    const questionWords = new Set(["WHAT", "WHERE", "WHO", "WHEN", "WHY", "HOW"]);
    const contentTokens = tokens.filter((t) => !questionWords.has(t.gloss));
    const qTokens = tokens.filter((t) => questionWords.has(t.gloss));
    const finalTokens = [...contentTokens, ...qTokens];

    return NextResponse.json({
      gloss: finalTokens.map((t) => t.gloss),
      tokens: finalTokens,
      nmm,
      tense: "present",
      dropped,
      fingerspelled,
      note: "Rule-based English to ISL gloss",
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ detail: msg }, { status: 500 });
  }
}
