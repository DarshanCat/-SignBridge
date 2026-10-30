"""Recognized sign labels -> gloss tokens."""

import re

from app.translation.vocabulary import Vocabulary


def normalize_gloss(labels: list[str]) -> list[str]:
    """Upper-case, hyphenate whitespace/underscores, drop empties and collapse immediate repeats."""
    out: list[str] = []
    for label in labels:
        token = re.sub(r"[\s_]+", "-", label.strip()).upper()
        if token and (not out or out[-1] != token):
            out.append(token)
    return out


def labels_to_gloss(labels: list[str], vocab: Vocabulary) -> tuple[list[str], list[str]]:
    """Return (gloss tokens, tokens missing from the vocabulary)."""
    gloss = normalize_gloss(labels)
    return gloss, [g for g in gloss if g not in vocab.glosses]
