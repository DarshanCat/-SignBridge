from pathlib import Path

import numpy as np
from fastapi import HTTPException

from app.recognition.artifacts import ModelLoadError
from app.recognition.inference import get_recognizer
from app.recognition.landmarks import process_sequence
from app.schemas.landmarks import LandmarkSequenceRequest
from app.schemas.recognition import RecognitionResponse, SignPrediction, SignTranslationResponse
from app.translation.gloss_to_english import gloss_to_english
from app.translation.labels import labels_to_gloss
from app.translation.vocabulary import Vocabulary


def recognize(req: LandmarkSequenceRequest, model_dir: Path) -> RecognitionResponse:
    """Run the trained model on a landmark sequence. Never fabricates output when no model is loaded."""
    try:
        recognizer = get_recognizer(model_dir)
    except ModelLoadError:
        raise HTTPException(
            status_code=503, detail="No trained recognition model is available, so signs cannot be recognized."
        ) from None

    processed = process_sequence(req)
    if not processed.usable:
        raise HTTPException(status_code=422, detail=" ".join(processed.warnings))

    rows = [f for f, rep in zip(processed.features, processed.frame_reports) if rep.valid]
    try:
        preds = recognizer.predict(np.array(rows, dtype=np.float32))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid landmark features: {exc}") from None
    return RecognitionResponse(
        predictions=[SignPrediction(label=p.label, confidence=p.confidence) for p in preds],
        num_frames_used=len(rows),
    )


def translate_signs(
    req: LandmarkSequenceRequest, model_dir: Path, vocab: Vocabulary, min_confidence: float
) -> SignTranslationResponse:
    """landmarks -> model -> label -> gloss -> English, for one isolated sign.

    The top prediction is accepted only if its model confidence reaches `min_confidence`; otherwise no gloss
    or English is produced. Continuous signing (several signs in one window) is not segmented.
    """
    rec = recognize(req, model_dir)
    top = rec.predictions[0]
    if top.confidence < min_confidence:
        return SignTranslationResponse(
            predictions=rec.predictions, num_frames_used=rec.num_frames_used, accepted=False,
            min_confidence=min_confidence, gloss=[], english="", unsupported=[],
            message=f"Top prediction confidence {top.confidence:.2f} is below the {min_confidence:.2f} threshold; no sign accepted.",
        )
    gloss, _ = labels_to_gloss([top.label], vocab)
    english = gloss_to_english(gloss, vocab)
    message = "Sign accepted." if not english.unsupported else "Sign accepted but it is not in the translation vocabulary."
    return SignTranslationResponse(
        predictions=rec.predictions, num_frames_used=rec.num_frames_used, accepted=True,
        min_confidence=min_confidence, gloss=english.gloss, english=english.english,
        unsupported=english.unsupported, message=message,
    )
