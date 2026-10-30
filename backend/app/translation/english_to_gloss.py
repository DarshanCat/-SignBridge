import re

from app.schemas.translation import EnglishToGlossResponse, WordResult
from app.translation.vocabulary import Vocabulary

TOKEN_RE = re.compile(r"[a-z']+")
NOTE = (
    "Rule-based baseline: stopword removal, phrase and word lookup, and an optional question-word-last rule. "
    "Not a full English-to-ISL translation; the vocabulary and rules are unvalidated placeholders."
)


def english_to_gloss(text: str, vocab: Vocabulary) -> EnglishToGlossResponse:
    words = TOKEN_RE.findall(text.lower())
    if not words:
        raise ValueError("Text contains no words.")

    stop = {w.lower() for w in vocab.stopwords}
    index = vocab.word_index()
    phrases = sorted(vocab.english_phrases, key=lambda p: len(p.words), reverse=True)

    results: list[WordResult] = []
    i = 0
    while i < len(words):
        phrase = next((p for p in phrases if [w.lower() for w in p.words] == words[i : i + len(p.words)]), None)
        if phrase:
            results.append(
                WordResult(word=" ".join(words[i : i + len(phrase.words)]), gloss=[g.upper() for g in phrase.gloss], status="mapped")
            )
            i += len(phrase.words)
            continue
        w = words[i]
        if w in index:
            results.append(WordResult(word=w, gloss=[index[w]], status="mapped"))
        elif w in stop:
            results.append(WordResult(word=w, gloss=[], status="dropped"))
        else:
            results.append(WordResult(word=w, gloss=[], status="unsupported"))
        i += 1

    gloss = [g for r in results for g in r.gloss]
    if vocab.rules.question_words_to_end:
        q = {g.upper() for g in vocab.rules.question_glosses}
        gloss = [g for g in gloss if g not in q] + [g for g in gloss if g in q]

    mapped = sum(r.status == "mapped" for r in results)
    unsupported = [r.word for r in results if r.status == "unsupported"]
    content = mapped + len(unsupported)
    return EnglishToGlossResponse(
        gloss=gloss,
        words=results,
        unsupported=unsupported,
        coverage=mapped / content if content else 0.0,
        note=NOTE,
    )
