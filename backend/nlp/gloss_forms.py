"""Gloss string conventions: upper case, words joined by hyphens, brackets become part of the name.

Examples: "you (plural)" -> YOU-PLURAL, "Race (ethnicity)" -> RACE-ETHNICITY, "Second (Number)" -> SECOND-NUMBER,
"Store or Shop" -> STORE-OR-SHOP (the dictionary also lists STORE and SHOP as English words for it).
"""

import re


def to_gloss(label: str) -> str:
    text = re.sub(r"[()]", " ", label.strip())
    text = text.replace(".", " ")
    text = re.sub(r"[^A-Za-z0-9\-]+", " ", text).strip()
    return re.sub(r"[\s\-]+", "-", text).upper()


FINGERSPELL_PREFIX = "FS:"


def is_fingerspelled(token: str) -> bool:
    return token.startswith(FINGERSPELL_PREFIX)
