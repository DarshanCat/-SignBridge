import logging
from pathlib import Path

from app.recognition.artifacts import LABELS_FILE, MODEL_FILE, ModelLoadError
from app.recognition.inference import get_recognizer
from app.schemas.status import ModelStatusResponse

logger = logging.getLogger("signbridge")


def get_model_status(model_dir: Path) -> ModelStatusResponse:
    """Report honestly whether trained artifacts exist and load."""
    model_path = model_dir / MODEL_FILE
    if not model_path.is_file() or not (model_dir / LABELS_FILE).is_file():
        return ModelStatusResponse(
            state="not_trained", loaded=False, model_path=f"{model_dir.name}/{MODEL_FILE}", classes=0,
            message="No trained ISL recognition model found. Recognition is disabled; no predictions are produced.",
        )
    try:
        rec = get_recognizer(model_dir)
    except ModelLoadError as exc:
        logger.warning("Model artifacts could not be loaded: %s", exc)  # detail stays in the server log
        return ModelStatusResponse(
            state="error", loaded=False, model_path=f"{model_dir.name}/{MODEL_FILE}", classes=0, message="Model artifacts exist but could not be loaded; see the server log."
        )
    return ModelStatusResponse(
        state="loaded", loaded=True, model_path=f"{model_dir.name}/{MODEL_FILE}", classes=len(rec.config.classes),
        message=f"Model loaded with {len(rec.config.classes)} sign class(es).",
    )
