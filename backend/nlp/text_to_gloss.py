"""Rule based English to ISL gloss using spaCy (tokenization, tags, lemmas, dependencies).

Rules applied to each clause, in this order of output: TIME first, then subject and other content in English order, then verbs
(subject object verb), then NOT, then modals, then question words last. Dropped: articles, copula and auxiliaries, prepositions,
the infinitive "to", "and", punctuation, intensifiers. Verbs and nouns are lemmatized. Possessives use the pronoun sign. Words missing
from the dictionary are fingerspelled. Negation and questions are reported as non manual markers (facial expression for the avatar).

These are simplified, ASSUMED rules for a prototype. They have not been validated by ISL signers or linguists and cover single clauses
with simple structure; they are not a complete model of ISL grammar.
"""

from dataclasses import dataclass, field

from nlp.fingerspell import fingerspell
from nlp.gloss_forms import FINGERSPELL_PREFIX
from nlp.lexicon import Lexicon, load_lexicon

DROP_ADVERBS = {"very", "much", "really", "just", "also", "too", "quite", "so", "then", "well"}
TIME_MODIFIERS = {"last", "next", "this"}
PAST_TIME = {"YESTERDAY", "BEFORE", "LAST"}
FUTURE_TIME = {"TOMORROW", "NEXT", "TONIGHT"}


@dataclass
class GlossToken:
    gloss: str
    kind: str  # sign or fingerspell
    source: str  # the English word(s) it came from
    letters: list[str] | None = None


@dataclass
class GlossResult:
    text: str
    gloss: list[str]
    tokens: list[GlossToken]
    nmm: list[str]  # non manual markers over the sentence: negation, wh-question, yes-no-question
    tense: str  # past, present or future (not marked on verbs; carried by time signs)
    dropped: list[dict] = field(default_factory=list)
    fingerspelled: list[str] = field(default_factory=list)

    @property
    def gloss_string(self) -> str:
        return " ".join(self.gloss)


@dataclass
class _Item:
    gloss: str
    role: str  # time, other, verb, neg, modal, wh
    source: str
    fs: bool = False
    letters: list[str] | None = None


def _clauses(sent) -> list[tuple[list, str | None]]:
    """Split a sentence at 'but' or 'and' when a verb follows, so each clause is ordered on its own. Returns (tokens, conjunction before it)."""
    toks = [t for t in sent]
    cut = [i for i, t in enumerate(toks) if t.pos_ == "CCONJ" and t.lower_ in {"but", "and"} and any(x.pos_ in {"VERB", "AUX"} for x in toks[i + 1 :])]
    out, start, conj = [], 0, None
    for i in cut:
        out.append((toks[start:i], conj))
        start, conj = i + 1, toks[i].lower_
    out.append((toks[start:], conj))
    return out


def _phrase_at(toks, i, lex: Lexicon):
    low = [t.lower_ for t in toks]
    for words, gloss in lex.phrases:
        n = len(words)
        if tuple(low[i : i + n]) == words:
            return n, gloss
    return 0, None


def _is_time_adverbial(tok, lex: Lexicon) -> bool:
    gloss = lex.lookup(tok.lemma_, tok.lower_)
    if not gloss or lex.pos(gloss) != "time":
        return False
    if gloss in {"YESTERDAY", "TODAY", "TOMORROW", "TONIGHT", "NOW"}:
        return True
    return tok.dep_ in {"npadvmod", "advmod", "tmod"} or (tok.dep_ == "pobj" and tok.head.lemma_ in {"in", "on", "at", "during", "by"})


def _clause_items(toks, lex: Lexicon, dropped: list[dict]) -> tuple[list[_Item], dict]:
    items: list[_Item] = []
    info = {"past": False, "future": False, "neg": False, "wh": False, "phrase_only": False}
    i = 0
    wh_set = lex.glosses_with_pos("wh")
    while i < len(toks):
        t = toks[i]
        n, pg = _phrase_at(toks, i, lex)
        if pg:
            role = "wh" if pg in wh_set else ("time" if lex.pos(pg) == "time" else "other")
            items.append(_Item(pg, role, " ".join(x.text for x in toks[i : i + n])))
            info["wh"] |= pg in wh_set
            i += n
            continue
        word, lemma = t.lower_, t.lemma_.lower()
        if t.is_punct or t.is_space:
            i += 1
            continue
        if t.dep_ == "neg" or lemma in {"not", "never"}:
            info["neg"] = True
            items.append(_Item("NOT", "neg", t.text))
            i += 1
            continue
        if t.pos_ == "DET" and lemma not in TIME_MODIFIERS and lex.pos(lex.lookup(lemma) or "") != "wh":
            dropped.append({"word": t.text, "reason": "article or determiner"})
            i += 1
            continue
        if lemma in TIME_MODIFIERS and t.head.pos_ in {"NOUN", "PROPN"} and lex.pos(lex.lookup(t.head.lemma_, t.head.lower_) or "") == "time":
            items.append(_Item(lex.lookup(lemma) or lemma.upper(), "time", t.text))
            info["past"] |= lemma == "last"
            info["future"] |= lemma == "next"
            i += 1
            continue
        if t.pos_ == "AUX":
            if lemma in {"can", "must"} and lex.lookup(lemma):
                items.append(_Item(lex.lookup(lemma), "modal", t.text))
            else:
                info["future"] |= lemma in {"will", "shall"}
                info["past"] |= t.tag_ == "VBD" and lemma in {"be", "do", "have"}
                dropped.append({"word": t.text, "reason": "copula or auxiliary"})
            i += 1
            continue
        if t.pos_ == "ADP" or (t.pos_ == "PART" and lemma in {"to", "'s"}):
            dropped.append({"word": t.text, "reason": "preposition or infinitive marker"})
            i += 1
            continue
        if t.pos_ == "CCONJ" and lemma in {"and"}:
            dropped.append({"word": t.text, "reason": "conjunction"})
            i += 1
            continue
        if word in DROP_ADVERBS:
            dropped.append({"word": t.text, "reason": "intensifier or filler (conveyed by facial expression)"})
            i += 1
            continue

        gloss = None
        if t.pos_ == "PRON":
            gloss = lex.pronoun_forms.get(word) or lex.lookup(word)
        if gloss is None:
            gloss = lex.lookup(lemma, word)
        if gloss is None:
            if t.pos_ == "PUNCT":
                i += 1
                continue
            token, letters = fingerspell(t.text if t.pos_ in {"PROPN", "NUM"} else t.lemma_ if t.pos_ == "VERB" else t.text)
            items.append(_Item(token, "verb" if t.pos_ == "VERB" else "other", t.text, fs=True, letters=letters))
            i += 1
            continue

        pos = lex.pos(gloss)
        if pos == "wh":
            info["wh"] = True
            role = "wh"
        elif pos == "neg":
            info["neg"] = True
            role = "neg"
        elif pos == "modal":
            role = "modal"
        elif _is_time_adverbial(t, lex):
            role = "time"
            info["past"] |= gloss in PAST_TIME
            info["future"] |= gloss in FUTURE_TIME
        elif pos == "verb" or t.pos_ == "VERB":
            role = "verb"
        else:
            role = "other"
        if t.tag_ in {"VBD", "VBN"} and t.pos_ == "VERB":
            info["past"] = True
        items.append(_Item(gloss, role, t.text))
        i += 1
    return items, info


PRONOUN_GLOSSES = {"I", "YOU", "HE", "SHE", "WE", "THEY", "IT"}


def _order(items: list[_Item]) -> list[_Item]:
    by = lambda r: [x for x in items if x.role == r]  # noqa: E731
    others: list[_Item] = []
    for it in by("other"):  # "I saw my brother" gives I I BROTHER; keep one pronoun sign when the same pronoun repeats directly
        if others and it.gloss == others[-1].gloss and it.gloss in PRONOUN_GLOSSES:
            continue
        others.append(it)
    return by("time") + others + by("verb") + by("neg") + by("modal") + by("wh")


def text_to_gloss(text: str, nlp, lex: Lexicon | None = None) -> GlossResult:
    lex = lex or load_lexicon()
    doc = nlp(text.strip())
    if not any(t.is_alpha or t.like_num for t in doc):
        raise ValueError("Text contains no words.")
    tokens: list[GlossToken] = []
    dropped: list[dict] = []
    nmm: list[str] = []
    past = future = False
    for sent in doc.sents:
        sent_has_wh = sent_neg = False
        phrase_only = True
        question = sent.text.strip().endswith("?")
        parts = _clauses(sent)
        for clause, conj in parts:
            items, info = _clause_items(clause, lex, dropped)
            sent_has_wh |= info["wh"]
            sent_neg |= info["neg"]
            phrase_only &= bool(items) and all(lex.pos(it.gloss) == "phrase" for it in items)
            past |= info["past"]
            future |= info["future"]
            ordered = _order(items)
            if conj == "but" and ordered:
                tokens.append(GlossToken("BUT", "sign", "but"))
            for it in ordered:
                tokens.append(GlossToken(it.gloss, "fingerspell" if it.fs else "sign", it.source, it.letters))
        if sent_neg and "negation" not in nmm:
            nmm.append("negation")
        if sent_has_wh and "wh-question" not in nmm:
            nmm.append("wh-question")
        elif question and not sent_has_wh and not phrase_only and "yes-no-question" not in nmm:
            nmm.append("yes-no-question")
    tokens = [t for t in tokens if t.gloss]
    tense = "past" if past and not future else "future" if future and not past else "present"
    return GlossResult(
        text=text, gloss=[t.gloss for t in tokens], tokens=tokens, nmm=nmm, tense=tense, dropped=dropped,
        fingerspelled=[t.gloss[len(FINGERSPELL_PREFIX):] for t in tokens if t.kind == "fingerspell"],
    )
