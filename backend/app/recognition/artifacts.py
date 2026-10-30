"""Model artifacts: weights plus the class mapping and preprocessing config they were trained with."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

from app.recognition.landmarks import FEATURE_DIM
from app.recognition.model import BiGRUClassifier

MODEL_FILE = "isl_model.pt"
LABELS_FILE = "labels.json"


class ModelLoadError(Exception):
    pass


@dataclass(frozen=True)
class ModelConfig:
    classes: list[str]
    feature_dim: int
    seq_len: int
    hidden: int = 128
    layers: int = 2
    dropout: float = 0.3


def save_artifacts(model: BiGRUClassifier, config: ModelConfig, model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_dir / MODEL_FILE)
    (model_dir / LABELS_FILE).write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


def load_artifacts(model_dir: Path) -> tuple[BiGRUClassifier, ModelConfig]:
    try:
        raw = json.loads((model_dir / LABELS_FILE).read_text(encoding="utf-8"))
        config = ModelConfig(**raw)
        if config.feature_dim != FEATURE_DIM:
            raise ValueError(f"model expects {config.feature_dim} features per frame but the pipeline produces {FEATURE_DIM}")
        if config.seq_len < 1 or len(config.classes) < 2:
            raise ValueError("invalid seq_len or class list in labels.json")
        model = BiGRUClassifier(config.feature_dim, len(config.classes), config.hidden, config.layers, config.dropout)
        model.load_state_dict(torch.load(model_dir / MODEL_FILE, map_location="cpu", weights_only=True))
    except Exception as exc:  # noqa: BLE001 - any unreadable or corrupt artifact (pickle, struct, shape errors) is a load error
        raise ModelLoadError(f"Could not load model artifacts: {exc}") from exc
    model.eval()
    return model, config
