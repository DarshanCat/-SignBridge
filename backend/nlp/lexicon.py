"""Gloss dictionary loading and lookups (config/gloss_dictionary.json)."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "gloss_dictionary.json"


@dataclass(frozen=True)
class Sign:
    gloss: str
    label: str
    pos: str
    source: str  # include (INCLUDE class) or grammar_placeholder (assumed, unvalidated)
    words: tuple[str, ...]
    category: str = ""


class Lexicon:
    def __init__(self, raw: dict) -> None:
        self.signs: dict[str, Sign] = {
            g: Sign(g, e["label"], e["pos"], e["source"], tuple(e["words"]), e.get("category", "")) for g, e in raw["signs"].items()
        }
        self.pronoun_forms: dict[str, str] = raw.get("pronoun_forms", {})
        self.word_index: dict[str, str] = {}
        for source in ("include", "grammar_placeholder"):  # INCLUDE entries win word conflicts
            for g, s in self.signs.items():
                if s.source == source:
                    for w in s.words:
                        self.word_index.setdefault(w.lower(), g)
        self.phrases: list[tuple[tuple[str, ...], str]] = sorted(
            ((tuple(w.split()), g) for w, g in self.word_index.items() if " " in w and "(" not in w),
            key=lambda p: len(p[0]), reverse=True,
        )

    def lookup(self, *words: str) -> str | None:
        for w in words:
            g = self.word_index.get(w.lower())
            if g:
                return g
        return None

    def pos(self, gloss: str) -> str:
        s = self.signs.get(gloss)
        return s.pos if s else "unknown"

    def english(self, gloss: str) -> str:
        """Base English word for a gloss (first listed word, else the lower cased label)."""
        s = self.signs.get(gloss)
        if s and s.words:
            return s.words[0]
        return s.label.lower() if s else gloss.lower().replace("-", " ")

    def glosses_with_pos(self, pos: str) -> set[str]:
        return {g for g, s in self.signs.items() if s.pos == pos}


@lru_cache(maxsize=2)
def load_lexicon(path: Path = DEFAULT_PATH) -> Lexicon:
    return Lexicon(json.loads(Path(path).read_text(encoding="utf-8")))
