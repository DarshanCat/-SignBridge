"""Rule based gloss to English for Module A output (recognized signs become a readable sentence).

Reverses the simplified gloss order: time signs first, then subject and objects, then the verb, then NOT and modals, then question
words. Inserts the function words that gloss omits (articles, the copula, auxiliaries, "to" after motion verbs) and conjugates verbs
using time signs (YESTERDAY or BEFORE give past, TOMORROW or NEXT give future, otherwise present). Fingerspelled tokens (FS:RAVI) are
written as names.

These are heuristics for a prototype with a tiny verb list; they are not a full ISL to English translator and cannot recover meaning
that the glosses do not carry (for example a missing time sign leaves the verb in the present tense).
"""

import re

from nlp.gloss_forms import FINGERSPELL_PREFIX, is_fingerspelled
from nlp.lexicon import Lexicon, load_lexicon

IRREGULAR_PAST = {"go": "went", "come": "came", "eat": "ate", "drink": "drank", "see": "saw", "know": "knew", "give": "gave",
                  "take": "took", "buy": "bought", "sleep": "slept", "write": "wrote", "read": "read", "meet": "met", "have": "had"}
MOTION = {"go", "come", "walk"}
PAST_TIME = {"YESTERDAY", "BEFORE", "LAST"}
FUTURE_TIME = {"TOMORROW", "NEXT", "TONIGHT"}
SUBJECT_FORMS = {"I": "I", "YOU": "you", "HE": "he", "SHE": "she", "WE": "we", "THEY": "they", "IT": "it", "YOU-PLURAL": "you all"}
OBJECT_FORMS = {"I": "me", "YOU": "you", "HE": "him", "SHE": "her", "WE": "us", "THEY": "them", "IT": "it", "YOU-PLURAL": "you all"}
POSSESSIVE = {"I": "my", "YOU": "your", "HE": "his", "SHE": "her", "WE": "our", "THEY": "their", "IT": "its", "YOU-PLURAL": "your"}
BE = {"I": "am", "YOU": "are", "WE": "are", "THEY": "are", "YOU-PLURAL": "are"}
THIRD_SINGULAR = {"HE", "SHE", "IT"}
QUESTION_PHRASES = {"HOW-ARE-YOU"}
NO_ARTICLE_POS = {"pron", "time", "phrase"}
DAYS = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"}
PARTS_OF_DAY = {"MORNING": "in the morning", "AFTERNOON": "in the afternoon", "EVENING": "in the evening", "NIGHT": "at night"}
PLURAL_BE = {"YOU", "WE", "THEY", "YOU-PLURAL"}


def _be(subject: str | None, past: bool, future: bool = False) -> str:
    """am, is, are, was, were, or will be, by the subject gloss (None or a noun counts as third person singular)."""
    if future:
        return "will be"
    if subject in PLURAL_BE:
        return "were" if past else "are"
    if subject == "I":
        return "was" if past else "am"
    return "was" if past else "is"


def _time_phrase(g: str, lex) -> str:
    """A time sign as it reads inside a sentence: on Monday, in the morning, at night, otherwise the plain word (today, yesterday)."""
    if g in DAYS:
        return "on " + lex.english(g).capitalize()
    if g in PARTS_OF_DAY:
        return PARTS_OF_DAY[g]
    return lex.english(g)


def _past(verb: str) -> str:
    if verb in IRREGULAR_PAST:
        return IRREGULAR_PAST[verb]
    return verb + ("d" if verb.endswith("e") else "ed")


def _third(verb: str) -> str:
    if re.search(r"(s|sh|ch|x|z|o)$", verb):
        return verb + "es"
    return verb[:-1] + "ies" if re.search(r"[^aeiou]y$", verb) else verb + "s"


def _word(g: str, lex: Lexicon) -> str:
    if is_fingerspelled(g):
        return g[len(FINGERSPELL_PREFIX):].capitalize()
    return lex.english(g)


def _article(word: str, definite: bool) -> str:
    return "the" if definite else ("an" if word[:1].lower() in "aeiou" else "a")


def _np(g: str, lex: Lexicon, definite: bool = True) -> str:
    """Noun phrase with an article (names, pronouns and time words get none)."""
    w = _word(g, lex)
    if is_fingerspelled(g) or lex.pos(g) in NO_ARTICLE_POS:
        return OBJECT_FORMS.get(g, w)
    return f"{_article(w, definite)} {w}"


def gloss_to_english(gloss: list[str], lex: Lexicon | None = None) -> str:
    lex = lex or load_lexicon()
    toks = [g.strip().upper() for g in gloss if g.strip()]
    if not toks:
        raise ValueError("No gloss tokens given.")
    clauses, cur = [], []
    for g in toks:
        if g == "BUT":
            clauses.append(cur)
            cur = []
        else:
            cur.append(g)
    clauses.append(cur)
    parts = [p for p in (_clause(c, lex) for c in clauses if c) if p]
    text = ", but ".join(p.rstrip(".?") for p in parts)
    end = "?" if parts and parts[-1].endswith("?") else "."
    return text[:1].upper() + text[1:] + end


def _clause(toks: list[str], lex: Lexicon) -> str:
    pos = lex.pos
    time = [g for g in toks if pos(g) == "time"]
    wh = [g for g in toks if pos(g) == "wh"]
    neg = any(pos(g) == "neg" for g in toks)
    modal = next((g for g in toks if pos(g) == "modal"), None)
    verbs = [g for g in toks if pos(g) == "verb"]
    rest = [g for g in toks if g not in time and g not in wh and pos(g) not in {"neg", "modal", "verb"}]
    past = any(g in PAST_TIME for g in time)
    future = any(g in FUTURE_TIME for g in time)
    time_text = " ".join(_time_phrase(g, lex) for g in time)
    time_plain = " ".join(_word(g, lex) for g in time)

    if len(toks) == 1 and pos(toks[0]) in {"phrase", "function"}:
        return _word(toks[0], lex).capitalize() + ("?" if toks[0] in QUESTION_PHRASES else ".")
    if any(g in QUESTION_PHRASES for g in toks):
        return " ".join(_word(g, lex) for g in toks).capitalize() + "?"
    if len(toks) >= 2 and pos(toks[0]) == "phrase" and all(pos(g) in {"noun", "unknown"} or is_fingerspelled(g) for g in toks[1:]):
        names = " ".join(_word(g, lex).capitalize() if is_fingerspelled(g) else _word(g, lex) for g in toks[1:])
        return f"{_word(toks[0], lex).capitalize()}, {names}."

    if verbs:
        return _verb_clause(rest, verbs, neg, modal, past, future, time_text, wh, lex)
    return _nominal_clause(rest, wh, neg, time_text, past, lex, future, time_plain)


def _subject(rest: list[str], lex: Lexicon) -> tuple[str, str | None, list[str]]:
    """Return (subject text, subject gloss for agreement, remaining tokens)."""
    if not rest:
        return "", None, []
    first = rest[0]
    if first in SUBJECT_FORMS:
        return SUBJECT_FORMS[first], first, rest[1:]
    return _np(first, lex), first, rest[1:]


def _verb_phrase(base: list[str], neg: bool, modal: str | None, past: bool, future: bool, third: bool) -> str:
    first = base[0]
    tail = f" to {base[1]}" if len(base) > 1 else ""
    if modal:
        aux = ("cannot" if neg else "can") if modal == "CAN" else ("must not" if neg else "must")
        return f"{aux} {first}{tail}"
    if future:
        return f"will {'not ' if neg else ''}{first}{tail}"
    if past:
        return f"did not {first}{tail}" if neg else f"{_past(first)}{tail}"
    if neg:
        return f"{'does not' if third else 'do not'} {first}{tail}"
    return f"{_third(first) if third else first}{tail}"


def _wh_question(w: str, subj: str, base: list[str], neg: bool, modal: str | None, past: bool, future: bool, third: bool, obj_text: list[str], time_text: str) -> str:
    """Question word plus an auxiliary: What do you want? Where did you go yesterday? What can you eat? Where will she go?"""
    first, tail = base[0], (f" to {base[1]}" if len(base) > 1 else "")
    if modal:
        aux = "can" if modal == "CAN" else "must"
    elif future:
        aux = "will"
    elif past:
        aux = "did"
    else:
        aux = "does" if third else "do"
    parts = [w, aux, subj, "not" if neg else "", first + tail, *obj_text, time_text]
    return " ".join(x for x in parts if x)


def _verb_clause(rest, verbs, neg, modal, past, future, time_text, wh, lex: Lexicon) -> str:
    subj, sg, objs = _subject(rest, lex)
    base = [lex.english(v) for v in verbs]
    third = sg in THIRD_SINGULAR or (sg is not None and sg not in SUBJECT_FORMS)
    vp = _verb_phrase(base, neg, modal, past, future, third)
    motion = base[-1] in MOTION
    obj_text = []
    for o in objs:
        txt = OBJECT_FORMS[o] if o in OBJECT_FORMS else "home" if o == "HOME" else _np(o, lex)
        if o == "HOME":
            pass  # "go home", no preposition or article
        elif motion and o not in OBJECT_FORMS and lex.pos(o) in {"noun", "unknown"}:
            txt = "to " + txt
        obj_text.append(txt)
    if wh:
        return _wh_question(_word(wh[0], lex), subj, base, neg, modal, past, future, third, obj_text, time_text).capitalize() + "?"
    sentence = " ".join(x for x in [subj, vp, *obj_text, time_text] if x)
    return sentence + "."


def _nominal_clause(rest: list[str], wh: list[str], neg: bool, time_text: str, past: bool, lex: Lexicon, future: bool = False, time_plain: str = "") -> str:
    if not rest and not wh:
        return (time_plain.capitalize() + ".") if time_plain else ""
    if wh:
        w = _word(wh[0], lex)
        if len(rest) == 2 and rest[0] in POSSESSIVE and lex.pos(rest[1]) in {"noun", "unknown"}:
            return f"{w} {'was' if past else 'is'} {POSSESSIVE[rest[0]]} {_word(rest[1], lex)}?".capitalize()
        if len(rest) == 2 and rest[0] in SUBJECT_FORMS and lex.pos(rest[1]) == "adj":  # "YOU HAPPY WHY" -> "Why are you happy?"
            return f"{w} {_be(rest[0], past)} {SUBJECT_FORMS[rest[0]]} {lex.english(rest[1])}?".capitalize()
        if len(rest) == 1 and rest[0] in BE:
            return f"{w} {_be(rest[0], past)} {SUBJECT_FORMS[rest[0]]}?".capitalize()
        phrase = " ".join(_np(g, lex) for g in rest)
        return f"{w} {'was' if past else 'is'} {phrase}?".capitalize()
    if len(rest) == 3 and rest[0] in POSSESSIVE and rest[1] == "NAME":  # "I NAME RAVI" -> "My name is Ravi."
        return f"{POSSESSIVE[rest[0]].capitalize()} name {'was' if past else 'is'} {_word(rest[2], lex)}."
    possessive = len(rest) >= 3 and rest[0] in POSSESSIVE and lex.pos(rest[1]) == "noun"  # "I BROTHER DOCTOR" -> "My brother is a doctor."
    if possessive:
        subj, sg, comp = f"{POSSESSIVE[rest[0]]} {_word(rest[1], lex)}", None, rest[2:]
    else:
        subj, sg, comp = _subject(rest, lex)
    be = _be(sg, past, future)
    if not comp:
        return f"{subj}{' ' + time_text if time_text else ''}."
    if len(comp) == 1 and lex.pos(comp[0]) == "adj":
        c = lex.english(comp[0])
    elif len(comp) == 1 and is_fingerspelled(comp[0]):
        c = _word(comp[0], lex)
    elif len(comp) == 1 and (sg in SUBJECT_FORMS or possessive) and lex.pos(comp[0]) in {"noun", "unknown"}:
        c = _np(comp[0], lex, definite=False)
    else:
        c = " ".join(_word(g, lex) for g in comp)
    not_ = " not" if neg else ""
    tail = f" {time_text}" if time_text else ""
    return f"{subj} {be}{not_} {c}{tail}."
