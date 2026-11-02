"""Live (WebSocket) recognition of isolated signs and building the English sentence from the accepted glosses.

The preprocessing is the training preprocessing: the same `process_sequence` (normalize_frame per frame, frames without a usable pose dropped)
as the REST endpoint and the dataset extraction, then `SignRecognizer.predict`, which applies `prepare_sequence` with the model's own
`seq_len` and `max_gap` from labels.json. Below the confidence threshold the output is UNRECOGNIZED and nothing is added to the sentence.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from pydantic import ValidationError

from app.recognition.artifacts import ModelLoadError
from app.recognition.inference import UNRECOGNIZED, get_recognizer
from app.recognition.landmarks import MIN_HAND_FRAMES, MIN_VALID_FRAMES, normalize_frame, process_sequence
from app.recognition.segmenter import SegmenterConfig, SignSegmenter
from app.schemas.landmarks import MAX_FRAMES, LandmarkFrame, LandmarkSequenceRequest
from nlp.gloss_to_text import gloss_to_english
from nlp.lexicon import Lexicon

THRESHOLD_FILE = "threshold.json"
MAX_SEQUENCE = 30  # accepted signs kept per connection


class LiveError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def load_threshold(model_dir: Path, default: float) -> tuple[float, str]:
    """Confidence threshold chosen on the validation split (models/threshold.json), else the configured default."""
    try:
        data = json.loads((model_dir / THRESHOLD_FILE).read_text(encoding="utf-8"))
        return float(data["threshold"]), "validation"
    except (OSError, ValueError, KeyError, TypeError):
        return default, "default"


def label_to_gloss(label: str, lex: Lexicon) -> str:
    """INCLUDE class label to the gloss used by the dictionary and the avatar (falls back to the upper cased, hyphenated label)."""
    low = label.strip().lower()
    for g, s in lex.signs.items():
        if s.source == "include" and s.label.lower() == low:
            return g
    return label.strip().upper().replace(" ", "-")


@dataclass
class LiveSession:
    """One WebSocket connection: the gloss sequence so far and the state of the sign segmenter."""

    sequence: list[str] = field(default_factory=list)
    segmenter: SignSegmenter = field(default_factory=SignSegmenter)
    frames_seen: int = 0  # frames received on the stream (with or without a usable pose)

    def reset(self) -> None:
        self.sequence.clear()
        self.segmenter.reset()
        self.frames_seen = 0

    def undo(self) -> str | None:
        """Remove the last recognized sign; returns its gloss, or None if the sentence was empty."""
        return self.sequence.pop() if self.sequence else None


def sentence_fields(session: LiveSession, lex: Lexicon) -> dict:
    return {"sequence": list(session.sequence), "english": gloss_to_english(session.sequence, lex) if session.sequence else ""}


def _classify(rows: np.ndarray, session: LiveSession, model_dir: Path, lex: Lexicon, default_threshold: float, commit: bool) -> dict:
    """Recognize one sign from normalized feature rows (valid frames only) and update the sentence."""
    try:
        recognizer = get_recognizer(model_dir)
    except ModelLoadError:
        raise LiveError("model_not_trained", "No trained sign recognition model is available.") from None
    preds = recognizer.predict(rows)
    threshold, source = load_threshold(model_dir, default_threshold)
    top = preds[0]
    accepted = top.confidence >= threshold
    out = {
        "type": "prediction",
        "accepted": accepted,
        "label": top.label if accepted else UNRECOGNIZED,
        "gloss": label_to_gloss(top.label, lex) if accepted else None,
        "confidence": top.confidence,
        "threshold": threshold,
        "threshold_source": source,
        "alternatives": [{"label": p.label, "confidence": p.confidence} for p in preds],
        "num_frames_used": int(len(rows)),
    }
    if accepted and commit:
        session.sequence.append(out["gloss"])
        del session.sequence[:-MAX_SEQUENCE]
    out.update(sentence_fields(session, lex))
    return out


def live_predict(message: dict, session: LiveSession, model_dir: Path, lex: Lexicon, default_threshold: float) -> dict:
    """One isolated sign from the frames in the message (the earlier, non-continuous mode)."""
    try:
        get_recognizer(model_dir)
    except ModelLoadError:
        raise LiveError("model_not_trained", "No trained sign recognition model is available.") from None
    try:
        req = LandmarkSequenceRequest.model_validate({"frames": message.get("frames")})
    except ValidationError:
        raise LiveError("bad_frames", "frames must be a list of 1 to 300 landmark frames (pose, left_hand, right_hand).") from None
    processed = process_sequence(req)
    if not processed.usable:
        raise LiveError("unusable_sequence", " ".join(processed.warnings))
    rows = np.array([f for f, r in zip(processed.features, processed.frame_reports) if r.valid], dtype=np.float32)
    return _classify(rows, session, model_dir, lex, default_threshold, bool(message.get("commit", True)))


def segment_events(rows: list[np.ndarray], session: LiveSession, model_dir: Path, lex: Lexicon, default_threshold: float) -> list[dict]:
    """Push normalized rows through the segmenter and classify every sign that finishes. Used by the stream handler and the evaluation."""
    events: list[dict] = []
    segments = []
    for row in rows:
        segments += session.segmenter.push(row)
    for seg in segments:
        hands = int(((seg.features[:, 99:] != 0).any(axis=1)).sum())
        info = {"start": seg.start, "end": seg.end, "frames": seg.frames}
        if len(seg.features) < MIN_VALID_FRAMES or hands < MIN_HAND_FRAMES:
            events.append({"type": "ignored", "reason": "too short or no hands visible", "segment": info})
            continue
        pred = _classify(seg.features.astype(np.float32), session, model_dir, lex, default_threshold, True)
        pred["type"] = "sign"
        pred["segment"] = info
        events.append(pred)
    return events


def live_stream(message: dict, session: LiveSession, model_dir: Path, lex: Lexicon, default_threshold: float) -> list[dict]:
    """A chunk of stream frames. Returns one `sign` event per finished sign, then a `stream` status message."""
    try:
        get_recognizer(model_dir)
    except ModelLoadError:
        raise LiveError("model_not_trained", "No trained sign recognition model is available.") from None
    raw = message.get("frames")
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_FRAMES:
        raise LiveError("bad_frames", "frames must be a list of 1 to 300 landmark frames (pose, left_hand, right_hand).")
    try:
        frames = [LandmarkFrame.model_validate(f) for f in raw]
    except ValidationError:
        raise LiveError("bad_frames", "frames must be a list of 1 to 300 landmark frames (pose, left_hand, right_hand).") from None
    rows = []
    for f in frames:
        feats, rep = normalize_frame(f)
        if rep.valid:
            rows.append(feats)
    session.frames_seen += len(frames)
    events = segment_events(rows, session, model_dir, lex, default_threshold)
    events.append({"type": "stream", "active": session.segmenter.active, "frames_seen": session.frames_seen, "usable_frames": len(rows), **sentence_fields(session, lex)})
    return events


def live_flush(session: LiveSession, model_dir: Path, lex: Lexicon, default_threshold: float) -> list[dict]:
    """Close a sign that is still open (the signer stopped with the hands up)."""
    events: list[dict] = []
    for seg in session.segmenter.flush():
        hands = int(((seg.features[:, 99:] != 0).any(axis=1)).sum())
        if len(seg.features) >= MIN_VALID_FRAMES and hands >= MIN_HAND_FRAMES:
            pred = _classify(seg.features.astype(np.float32), session, model_dir, lex, default_threshold, True)
            pred["type"] = "sign"
            pred["segment"] = {"start": seg.start, "end": seg.end, "frames": seg.frames}
            events.append(pred)
    events.append({"type": "stream", "active": False, "frames_seen": session.frames_seen, **sentence_fields(session, lex)})
    return events
