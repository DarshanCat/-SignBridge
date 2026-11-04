"""The conversation vocabulary (config/conversation_vocabulary.json): which signs the model already knows (INCLUDE classes) and which must be recorded."""

import json
from dataclasses import dataclass
from pathlib import Path

from app.recording import GLOSS_RE

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "conversation_vocabulary.json"
GROUPS = ("question", "pronoun", "verb", "answer", "greeting", "extra")


@dataclass(frozen=True)
class VocabSign:
    gloss: str
    group: str
    include_class: str | None
    note: str = ""

    @property
    def must_record(self) -> bool:
        return self.include_class is None


@dataclass(frozen=True)
class ConversationVocabulary:
    signs: tuple[VocabSign, ...]
    test_sentences: tuple[str, ...]

    def to_record(self) -> list[str]:
        return [s.gloss for s in self.signs if s.must_record]

    def known(self) -> list[str]:
        return [s.gloss for s in self.signs if not s.must_record]


def load_vocabulary(path: Path = DEFAULT_PATH) -> ConversationVocabulary:
    raw = json.loads(path.read_text(encoding="utf-8"))
    signs = tuple(VocabSign(e["gloss"], e["group"], e["include_class"], e.get("note", "")) for e in raw["signs"])
    seen: set[str] = set()
    for s in signs:
        if not GLOSS_RE.match(s.gloss) or s.gloss in seen or s.group not in GROUPS:
            raise ValueError(f"invalid or duplicate vocabulary entry {s.gloss!r}")
        seen.add(s.gloss)
    return ConversationVocabulary(signs, tuple(raw["test_sentences"]))
