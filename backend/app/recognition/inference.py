from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from app.recognition.artifacts import ModelConfig, load_artifacts
from app.recognition.preprocess import prepare_sequence_full


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float


class SignRecognizer:
    def __init__(self, model: torch.nn.Module, config: ModelConfig) -> None:
        self.model = model
        self.config = config

    @torch.no_grad()
    def predict(self, features: np.ndarray, top_k: int = 3) -> list[Prediction]:
        """Softmax probabilities from the trained model for one (T, FEATURE_DIM) sequence."""
        x = torch.from_numpy(prepare_sequence_full(features, self.config.seq_len, self.config.max_gap)).unsqueeze(0)
        probs = torch.softmax(self.model(x), dim=-1)[0]
        k = min(top_k, len(self.config.classes))
        vals, idx = torch.topk(probs, k)
        return [Prediction(self.config.classes[i], float(v)) for v, i in zip(vals.tolist(), idx.tolist())]


UNRECOGNIZED = "UNRECOGNIZED"


def label_or_unrecognized(predictions: list[Prediction], threshold: float) -> str:
    """Top label if its model confidence reaches `threshold`, else the explicit UNRECOGNIZED output (never forced into a class)."""
    if not predictions or predictions[0].confidence < threshold:
        return UNRECOGNIZED
    return predictions[0].label


_cache: dict[tuple[str, int], SignRecognizer] = {}


def get_recognizer(model_dir: Path) -> SignRecognizer:
    """Load (and cache by file mtime) the recognizer; raises ModelLoadError if unavailable."""
    from app.recognition.artifacts import MODEL_FILE, ModelLoadError

    path = model_dir / MODEL_FILE
    try:
        key = (str(path), path.stat().st_mtime_ns)
    except OSError as exc:
        raise ModelLoadError(f"Model file not found: {path}") from exc
    if key not in _cache:
        _cache.clear()
        model, config = load_artifacts(model_dir)
        _cache[key] = SignRecognizer(model, config)
    return _cache[key]
