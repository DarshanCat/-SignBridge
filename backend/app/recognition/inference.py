from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from app.recognition.artifacts import ModelConfig, load_artifacts
from app.recognition.preprocess import resample_sequence


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
        x = torch.from_numpy(resample_sequence(features, self.config.seq_len)).unsqueeze(0)
        probs = torch.softmax(self.model(x), dim=-1)[0]
        k = min(top_k, len(self.config.classes))
        vals, idx = torch.topk(probs, k)
        return [Prediction(self.config.classes[i], float(v)) for v, i in zip(vals.tolist(), idx.tolist())]


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
