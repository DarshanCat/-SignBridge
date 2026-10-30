"""Build backend/config/gloss_dictionary.json. Run once from backend/ (reads the class list and the authors' split lists, writes a small JSON):

    python -m nlp.build_dictionary --splits ..\data\raw\include\splits --out config\gloss_dictionary.json

INCLUDE class names (the only signs a recognition model can learn from this dataset) get a part of speech from their INCLUDE category.
A small set of grammar and function signs that INCLUDE does not contain (GO, WHERE, WHAT, NOT, ...) is added as PLACEHOLDER entries:
they are common ISL lexicon items by assumption, have no recognition data and no animation, and have not been validated by ISL signers.
"""

import argparse
import json
import re
from pathlib import Path

from nlp.gloss_forms import to_gloss

CATEGORY_POS = {
    "Adjectives": "adj", "Colours": "adj", "Pronouns": "pron", "Days_and_Time": "time", "Greetings": "phrase",
}
# INCLUDE labels that are not plain nouns
POS_OVERRIDES = {"Alright": "adj", "Pleased": "adj", "Nice": "adj", "alive": "adj", "Ex. Monsoon": "noun"}
EXTRA_WORDS = {  # label -> English words that should map to it (beyond the label itself)
    "Store or Shop": ["store", "shop"], "Street or Road": ["street", "road"], "big large": ["big", "large"],
    "small little": ["small", "little"], "Cell phone": ["cell phone", "mobile phone", "mobile"], "Ex. Monsoon": ["monsoon"],
    "Clothing": ["clothes", "clothing"], "Telephone": ["telephone", "phone"], "T-Shirt": ["t-shirt", "tshirt"],
    "Photograph": ["photograph", "photo"], "you (plural)": ["you all", "you guys", "y'all"],
    "Race (ethnicity)": ["race", "ethnicity"], "Second (Number)": [], "Transportation": ["transportation", "transport"], "Colour": ["colour", "color"],
}
GRAMMAR_SIGNS = {  # gloss -> (pos, english words); PLACEHOLDERS, not in INCLUDE, unvalidated
    "GO": ("verb", ["go"]), "COME": ("verb", ["come"]), "EAT": ("verb", ["eat"]), "DRINK": ("verb", ["drink"]),
    "WANT": ("verb", ["want"]), "NEED": ("verb", ["need"]), "HELP": ("verb", ["help"]), "SEE": ("verb", ["see"]),
    "KNOW": ("verb", ["know"]), "LIKE": ("verb", ["like"]), "LOVE": ("verb", ["love"]), "WORK": ("verb", ["work"]),
    "STUDY": ("verb", ["study"]), "GIVE": ("verb", ["give"]), "TAKE": ("verb", ["take"]), "BUY": ("verb", ["buy"]),
    "SLEEP": ("verb", ["sleep"]), "WALK": ("verb", ["walk"]), "READ": ("verb", ["read"]), "WRITE": ("verb", ["write"]),
    "LIVE": ("verb", ["live"]), "MEET": ("verb", ["meet"]), "STAY": ("verb", ["stay"]),
    "WHAT": ("wh", ["what"]), "WHERE": ("wh", ["where"]), "WHO": ("wh", ["who", "whom"]), "WHY": ("wh", ["why"]),
    "WHEN": ("wh", ["when"]), "HOW": ("wh", ["how"]), "WHICH": ("wh", ["which"]),
    "NOT": ("neg", ["not", "never"]), "NO": ("function", ["no"]), "HAVE": ("verb", ["have"]), "CAN": ("modal", ["can"]), "MUST": ("modal", ["must"]),
    "NAME": ("noun", ["name"]), "WATER": ("noun", ["water"]), "HOME": ("noun", ["home"]), "FOOD": ("noun", ["food"]), "PLEASE": ("function", ["please"]), "YES": ("function", ["yes"]),
    "BUT": ("function", ["but"]), "OR": ("function", ["or"]), "NOW": ("time", ["now"]), "BEFORE": ("time", ["before", "ago"]),
    "LAST": ("time", ["last"]), "NEXT": ("time", ["next"]), "THIS": ("time", ["this"]), "TONIGHT": ("time", ["tonight"]),
    "ALL": ("function", ["all"]), "YOU-PLURAL": ("pron", ["you all", "you guys", "y'all"]),
}
EXTRA_PRON = {"my": "I", "me": "I", "mine": "I", "myself": "I", "your": "YOU", "yours": "YOU", "his": "HE", "him": "HE",
              "her": "SHE", "hers": "SHE", "our": "WE", "us": "WE", "their": "THEY", "them": "THEY", "its": "IT"}


def build(splits: Path) -> dict:
    cat_of: dict[str, str] = {}
    for name in ("include_train.txt", "include_val.txt", "include_test.txt"):
        for line in (splits / name).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not re.search(r"\.(mov|mp4)$", line, re.I):
                continue
            parts = line.split("/")
            folder = parts[1]
            label = re.sub(r"^\s*\d+\.\s*", "", folder).strip()
            cat_of.setdefault(label, parts[0])
    entries: dict[str, dict] = {}
    for label, cat in sorted(cat_of.items(), key=lambda kv: kv[0].lower()):
        g = to_gloss(label)
        low = label.lower()
        words = EXTRA_WORDS.get(label) or ([w.strip() for w in low.split(" or ")] if " or " in low else [re.sub(r"\.", "", low).strip()])
        entries[g] = {"label": label, "category": cat, "pos": POS_OVERRIDES.get(label, CATEGORY_POS.get(cat, "noun")),
                      "words": sorted(set(words)), "source": "include"}
    for g, (pos, words) in GRAMMAR_SIGNS.items():
        entries.setdefault(g, {"label": g.title(), "category": "grammar", "pos": pos, "words": words, "source": "grammar_placeholder"})
    # pronoun entries needed by the rules
    for g, label in (("HE", "he"), ("SHE", "she"), ("IT", "it"), ("THEY", "they"), ("WE", "we"), ("YOU", "you"), ("I", "I")):
        entries.setdefault(g, {"label": label, "category": "Pronouns", "pos": "pron", "words": [label.lower()], "source": "include"})
    return {
        "_notice": "Entries with source include are INCLUDE class names. Entries with source grammar_placeholder are assumed ISL lexicon items "
                   "that INCLUDE does not contain; they are unvalidated, have no recognition data and no animation.",
        "pronoun_forms": EXTRA_PRON,
        "signs": entries,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--splits", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    d = build(a.splits)
    a.out.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    src = {}
    for e in d["signs"].values():
        src[e["source"]] = src.get(e["source"], 0) + 1
    print(f"wrote {len(d['signs'])} signs {src} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
