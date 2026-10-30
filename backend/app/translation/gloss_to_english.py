from app.schemas.translation import GlossToEnglishResponse
from app.translation.labels import normalize_gloss
from app.translation.vocabulary import Vocabulary

NOTE = (
    "Token-by-token lookup with a few configured phrase patterns. This is not grammatical ISL-to-English "
    "translation; supported glosses and phrases come from the unvalidated placeholder vocabulary."
)


def gloss_to_english(gloss: list[str], vocab: Vocabulary) -> GlossToEnglishResponse:
    tokens = normalize_gloss(gloss)
    phrases = sorted(vocab.gloss_phrases, key=lambda p: len(p.gloss), reverse=True)
    question = {g.upper() for g in vocab.rules.question_glosses}

    parts: list[str] = []
    unsupported: list[str] = []
    is_question = False
    i = 0
    while i < len(tokens):
        phrase = next((p for p in phrases if [g.upper() for g in p.gloss] == tokens[i : i + len(p.gloss)]), None)
        if phrase:
            parts.append(phrase.english)
            is_question = is_question or phrase.english.rstrip().endswith("?")
            i += len(phrase.gloss)
            continue
        entry = vocab.glosses.get(tokens[i])
        if entry:
            parts.append(entry.english)
            is_question = is_question or tokens[i] in question
        else:
            unsupported.append(tokens[i])
        i += 1

    english = " ".join(parts)
    if english and english[-1] not in ".?!":
        english += "?" if is_question else "."
    if english:
        english = english[0].upper() + english[1:]
    return GlossToEnglishResponse(english=english, gloss=tokens, unsupported=unsupported, note=NOTE)
