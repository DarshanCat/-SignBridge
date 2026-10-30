"""Configurable vocabulary and rules for the rule-based translation baseline."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator


class GlossEntry(BaseModel):
    english: str
    words: list[str] = Field(default_factory=list)


class EnglishPhrase(BaseModel):
    words: list[str]
    gloss: list[str]


class GlossPhrase(BaseModel):
    gloss: list[str]
    english: str


class Rules(BaseModel):
    question_words_to_end: bool = False
    question_glosses: list[str] = Field(default_factory=list)


class Vocabulary(BaseModel):
    stopwords: list[str] = Field(default_factory=list)
    glosses: dict[str, GlossEntry]
    english_phrases: list[EnglishPhrase] = Field(default_factory=list)
    gloss_phrases: list[GlossPhrase] = Field(default_factory=list)
    rules: Rules = Field(default_factory=Rules)

    @field_validator("glosses")
    @classmethod
    def _glosses_not_empty(cls, v: dict[str, GlossEntry]) -> dict[str, GlossEntry]:
        if not v:
            raise ValueError("glosses must not be empty")
        return {k.strip().upper(): e for k, e in v.items()}

    def word_index(self) -> dict[str, str]:
        """Lower-case English word -> gloss (first definition wins)."""
        index: dict[str, str] = {}
        for gloss, entry in self.glosses.items():
            for w in entry.words:
                index.setdefault(w.lower(), gloss)
        return index


class VocabularyError(Exception):
    pass


def load_vocabulary(path: Path) -> Vocabulary:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Vocabulary.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise VocabularyError(f"Could not load translation config {path}: {exc}") from exc


@lru_cache(maxsize=4)
def _cached(path: str, mtime_ns: int) -> Vocabulary:
    return load_vocabulary(Path(path))


def get_vocabulary(path: Path) -> Vocabulary:
    try:
        return _cached(str(path), path.stat().st_mtime_ns)
    except OSError as exc:
        raise VocabularyError(f"Translation config not found: {path}") from exc
