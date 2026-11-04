"""Conversation module: the vocabulary (known and to record), the signs the loaded model can recognize, and the test sentences."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.conversation_vocab import ConversationVocabulary, load_vocabulary
from app.core.config import Settings, get_settings
from app.recognition.artifacts import LABELS_FILE, MODEL_FILE
from app.recognition.inference import get_recognizer
from nlp.gloss_forms import to_gloss

router = APIRouter(prefix="/api")


class VocabItem(BaseModel):
    gloss: str
    group: str
    include_class: str | None
    must_record: bool
    note: str


class VocabularyOut(BaseModel):
    signs: list[VocabItem]
    known: int
    to_record: int
    test_sentences: list[str]


class KnownSign(BaseModel):
    gloss: str
    label: str


class KnownSignsOut(BaseModel):
    loaded: bool
    count: int
    signs: list[KnownSign]
    note: str = "Every class the loaded model can output. Below the confidence threshold the answer is UNRECOGNIZED. Authors' predefined split, signer independence not verified."


def get_conversation_vocabulary() -> ConversationVocabulary:
    try:
        return load_vocabulary()
    except (OSError, ValueError, KeyError):
        raise HTTPException(status_code=503, detail="The conversation vocabulary file is missing or invalid.") from None


@router.get("/conversation/vocabulary", response_model=VocabularyOut)
def conversation_vocabulary(v: ConversationVocabulary = Depends(get_conversation_vocabulary)) -> VocabularyOut:
    items = [VocabItem(gloss=s.gloss, group=s.group, include_class=s.include_class, must_record=s.must_record, note=s.note) for s in v.signs]
    return VocabularyOut(signs=items, known=len(v.known()), to_record=len(v.to_record()), test_sentences=list(v.test_sentences))


@router.get("/model/signs", response_model=KnownSignsOut)
def model_signs(settings: Settings = Depends(get_settings)) -> KnownSignsOut:
    """The class names of the loaded model (loaded=false and empty when there is none)."""
    if not (settings.model_dir / MODEL_FILE).is_file() or not (settings.model_dir / LABELS_FILE).is_file():
        return KnownSignsOut(loaded=False, count=0, signs=[])
    try:
        classes = get_recognizer(settings.model_dir).config.classes
    except Exception:  # noqa: BLE001 - reported as not loaded; the detail is in the model status log
        return KnownSignsOut(loaded=False, count=0, signs=[])
    signs = sorted((KnownSign(gloss=to_gloss(c), label=c) for c in classes), key=lambda s: s.label.lower())
    return KnownSignsOut(loaded=True, count=len(signs), signs=signs)
