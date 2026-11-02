"""Text to gloss and gloss to text (spaCy rules), plus the live prediction WebSocket (stub until a model is trained)."""

import json
import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings, origin_allowed
from app.recognition.model_status import get_model_status
from nlp.gloss_to_text import gloss_to_english
from nlp.lexicon import Lexicon, load_lexicon
from nlp.text_to_gloss import text_to_gloss

logger = logging.getLogger("signbridge")
router = APIRouter()

NOTE = (
    "Simplified rule based English to ISL gloss (drop articles, copula and auxiliaries; time first; subject object verb; question words "
    "last; fingerspelling for unknown words). Assumed rules, not validated by ISL signers. Entries marked grammar_placeholder in the "
    "dictionary are unvalidated and have no animation."
)


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class GlossTokenOut(BaseModel):
    gloss: str
    kind: str
    source: str
    letters: list[str] | None = None


class TextToGlossResponse(BaseModel):
    gloss: list[str]
    tokens: list[GlossTokenOut]
    nmm: list[str]
    tense: str
    dropped: list[dict]
    fingerspelled: list[str]
    note: str = NOTE


class GlossRequest(BaseModel):
    gloss: list[str] = Field(min_length=1, max_length=50)


class GlossToTextResponse(BaseModel):
    english: str
    note: str = "Heuristic gloss to English; verbs and word order are reconstructed from a few rules and time signs."


@lru_cache(maxsize=2)
def _load_nlp(model_name: str):
    import spacy

    return spacy.load(model_name)


def get_nlp(settings: Settings = Depends(get_settings)):
    try:
        return _load_nlp(settings.spacy_model)
    except (ImportError, OSError):
        logger.warning("spaCy model %s is not installed", settings.spacy_model)
        raise HTTPException(status_code=503, detail="The NLP model is not installed on the server.") from None


def get_lexicon(settings: Settings = Depends(get_settings)) -> Lexicon:
    try:
        return load_lexicon(settings.gloss_dictionary)
    except (OSError, ValueError, KeyError):
        raise HTTPException(status_code=503, detail="The gloss dictionary is unavailable or invalid.") from None


@router.post("/api/nlp/text-to-gloss", response_model=TextToGlossResponse)
def api_text_to_gloss(req: TextRequest, nlp=Depends(get_nlp), lex: Lexicon = Depends(get_lexicon)) -> TextToGlossResponse:
    try:
        r = text_to_gloss(req.text, nlp, lex)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return TextToGlossResponse(
        gloss=r.gloss, tokens=[GlossTokenOut(**t.__dict__) for t in r.tokens], nmm=r.nmm, tense=r.tense,
        dropped=r.dropped, fingerspelled=r.fingerspelled,
    )


@router.post("/api/nlp/gloss-to-text", response_model=GlossToTextResponse)
def api_gloss_to_text(req: GlossRequest, lex: Lexicon = Depends(get_lexicon)) -> GlossToTextResponse:
    try:
        return GlossToTextResponse(english=gloss_to_english(req.gloss, lex))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.websocket("/ws/predict")
async def ws_predict(ws: WebSocket) -> None:
    """Live isolated sign recognition. Client messages (JSON text):
        {"type": "predict", "frames": [LandmarkFrame, ...], "commit": true}   recognize one sign from the frames
        {"type": "reset"}                                                      clear the sentence and the segmenter
        {"type": "frames", "frames": [...]}                                    continuous mode: stream frames in chunks; every finished sign
                                                                               comes back as a `sign` event, followed by a `stream` status
        {"type": "undo"} / {"type": "flush"}                                   remove the last sign / close a sign still open
    Server messages: ready, prediction, reset_ok, error. Without a trained model it sends model_not_trained and closes; it never invents
    a prediction. Below the confidence threshold the label is UNRECOGNIZED and the sentence is unchanged."""
    settings = get_settings()
    if settings.ws_check_origin and not origin_allowed(ws.headers.get("origin"), settings):
        await ws.close(code=1008)  # policy violation: the page is not on the list of allowed origins
        return
    await ws.accept()
    status = get_model_status(settings.model_dir)
    if status.state != "loaded":
        await ws.send_json({"type": "error", "error": "model_not_trained", "message": "No trained sign recognition model is available; streaming prediction is disabled."})
        await ws.close(code=1013)  # 1013: try again later
        return
    try:
        lex = load_lexicon(settings.gloss_dictionary)
    except (OSError, ValueError, KeyError):
        await ws.send_json({"type": "error", "error": "dictionary_unavailable", "message": "The gloss dictionary is unavailable or invalid."})
        await ws.close(code=1011)
        return
    from app.recognition.inference import get_recognizer
    from app.services.live_service import LiveError, LiveSession, live_flush, live_predict, live_stream, load_threshold, sentence_fields

    config = get_recognizer(settings.model_dir).config
    threshold, source = load_threshold(settings.model_dir, settings.min_confidence)
    await ws.send_json({"type": "ready", "classes": len(config.classes), "architecture": config.arch, "threshold": threshold, "threshold_source": source})
    session = LiveSession()
    try:
        while True:
            raw = await ws.receive_text()
            if len(raw) > settings.max_body_bytes:
                await ws.send_json({"type": "error", "error": "too_large", "message": "Message too large."})
                continue
            try:
                msg = json.loads(raw)
                kind = msg.get("type") if isinstance(msg, dict) else None
            except ValueError:
                kind, msg = None, {}
            if kind == "reset":
                session.reset()
                await ws.send_json({"type": "reset_ok"})
            elif kind == "undo":
                removed = session.undo()
                await ws.send_json({"type": "sequence", "removed": removed, **sentence_fields(session, lex)})
            elif kind == "flush":
                for ev in live_flush(session, settings.model_dir, lex, settings.min_confidence):
                    await ws.send_json(ev)
            elif kind == "frames":
                try:
                    for ev in live_stream(msg, session, settings.model_dir, lex, settings.min_confidence):
                        await ws.send_json(ev)
                except LiveError as exc:
                    await ws.send_json({"type": "error", "error": exc.code, "message": exc.message})
            elif kind == "predict":
                try:
                    await ws.send_json(live_predict(msg, session, settings.model_dir, lex, settings.min_confidence))
                except LiveError as exc:
                    await ws.send_json({"type": "error", "error": exc.code, "message": exc.message})
            else:
                await ws.send_json({"type": "error", "error": "bad_message", "message": "Expected a JSON message with type frames, predict, undo, flush or reset."})
    except WebSocketDisconnect:
        return
