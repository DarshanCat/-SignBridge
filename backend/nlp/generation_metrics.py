"""Scores for the generation directions (English to gloss, gloss to English) against references that a signer or translator wrote.

BLEU: corpus level, 4-gram, brevity penalty, several references per sentence, with sacreBLEU's default "exp" smoothing for orders without a match
(a short sentence rarely shares a 4-gram, so unsmoothed BLEU would be 0). Gloss accuracy: sentence exact match (against any reference), gloss word
error rate (edit distance to the closest reference over its length), and the F1 of the bag of gloss tokens. All of them are computed here,
no library; the tests check them against hand worked values.

Tokenization: English is lower cased and split into words and punctuation marks; gloss is split on spaces and keeps its case (a gloss is an
upper case convention, FS:RAVI is one token).
"""

import math
import re
from collections import Counter

MAX_ORDER = 4


def tokenize_english(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?|[^\sa-z0-9]", text.lower())


def tokenize_gloss(text: str) -> list[str]:
    return text.split()


def _ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def bleu(hypotheses: list[list[str]], references: list[list[list[str]]], smooth: bool = True) -> dict:
    """Corpus BLEU-4 (0 to 100). references[i] is the list of reference token lists of sentence i."""
    if len(hypotheses) != len(references) or not hypotheses:
        raise ValueError("need the same, non zero number of hypotheses and reference lists")
    matches = [0] * MAX_ORDER
    totals = [0] * MAX_ORDER
    hyp_len = ref_len = 0
    for hyp, refs in zip(hypotheses, references):
        if not refs or any(not r for r in refs):
            raise ValueError("every sentence needs at least one non empty reference")
        hyp_len += len(hyp)
        ref_len += min((abs(len(r) - len(hyp)), len(r)) for r in refs)[1]  # the closest reference length (shorter on a tie)
        for n in range(1, MAX_ORDER + 1):
            h = _ngrams(hyp, n)
            best: Counter = Counter()
            for r in refs:
                for g, c in _ngrams(r, n).items():
                    best[g] = max(best[g], c)
            matches[n - 1] += sum(min(c, best[g]) for g, c in h.items())
            totals[n - 1] += max(len(hyp) - n + 1, 0)
    precisions: list[float] = []
    k = 1.0
    for m, t in zip(matches, totals):
        if t == 0:
            precisions.append(0.0)
        elif m == 0:
            if smooth:
                k *= 2
                precisions.append(1.0 / (k * t))
            else:
                precisions.append(0.0)
        else:
            precisions.append(m / t)
    if hyp_len == 0 or min(precisions) <= 0:
        score = 0.0
    else:
        bp = 1.0 if hyp_len > ref_len else math.exp(1 - ref_len / hyp_len)
        score = 100.0 * bp * math.exp(sum(math.log(p) for p in precisions) / MAX_ORDER)
    return {"bleu": score, "precisions": [100.0 * p for p in precisions], "hyp_len": hyp_len, "ref_len": ref_len,
            "brevity_penalty": 1.0 if hyp_len > ref_len or hyp_len == 0 else math.exp(1 - ref_len / hyp_len)}


def edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def gloss_word_error_rate(hyps: list[list[str]], refs: list[list[list[str]]]) -> float:
    """Total edit distance to the closest reference of every sentence over the total length of those closest references."""
    errors = length = 0
    for h, rs in zip(hyps, refs):
        d, r = min((edit_distance(h, r), r) for r in rs)
        errors += d
        length += len(r)
    return errors / length if length else 0.0


def bag_f1(hyp: list[str], refs: list[list[str]]) -> float:
    """F1 of the multiset of gloss tokens against the best reference (order ignored)."""
    best = 0.0
    for r in refs:
        overlap = sum((Counter(hyp) & Counter(r)).values())
        if overlap == 0:
            continue
        p, rec = overlap / len(hyp), overlap / len(r)
        best = max(best, 2 * p * rec / (p + rec))
    return best


def gloss_scores(hyps: list[list[str]], refs: list[list[list[str]]]) -> dict:
    exact = [h in rs for h, rs in zip(hyps, refs)]
    return {
        "sentences": len(hyps),
        "exact_match": sum(exact) / len(hyps),
        "word_error_rate": gloss_word_error_rate(hyps, refs),
        "token_accuracy": max(0.0, 1.0 - gloss_word_error_rate(hyps, refs)),
        "bag_f1": sum(bag_f1(h, rs) for h, rs in zip(hyps, refs)) / len(hyps),
        "bleu": bleu(hyps, refs),
    }
