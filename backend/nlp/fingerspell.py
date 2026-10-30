"""Fingerspelling fallback: a word that is not in the sign dictionary is spelled letter by letter.

Fingerspelling is a real part of sign language, used mainly for names and technical terms. Each letter is a separate manual
alphabet clip (none exist yet in this project). Digits are spelled the same way and flagged as digits.
"""

import re

from nlp.gloss_forms import FINGERSPELL_PREFIX


def fingerspell(word: str) -> tuple[str, list[str]]:
    """Return (gloss token such as 'FS:RAVI', its letters). Non alphanumeric characters are removed."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", word).upper()
    if not cleaned:
        raise ValueError("nothing to fingerspell")
    return FINGERSPELL_PREFIX + cleaned, list(cleaned)
