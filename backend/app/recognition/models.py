"""Sequence classifiers over landmark features: (B, T, F) -> logits (B, C). One factory builds all of them from a ModelConfig."""

import math
from typing import TYPE_CHECKING

import torch
from torch import nn

from app.recognition.model import BiGRUClassifier

if TYPE_CHECKING:
    from app.recognition.artifacts import ModelConfig

ARCHITECTURES = ("cnn", "bigru", "transformer")


class CNN1DClassifier(nn.Module):
    """1D temporal CNN baseline: three conv blocks over time, global average and max pooling, linear head."""

    def __init__(self, feature_dim: int, num_classes: int, hidden: int = 128, dropout: float = 0.3) -> None:
        super().__init__()
        c = hidden
        self.net = nn.Sequential(
            nn.Conv1d(feature_dim, c, kernel_size=5, padding=2), nn.BatchNorm1d(c), nn.ReLU(),
            nn.Conv1d(c, c, kernel_size=5, padding=2), nn.BatchNorm1d(c), nn.ReLU(),
            nn.Conv1d(c, c, kernel_size=3, padding=1), nn.BatchNorm1d(c), nn.ReLU(),
        )
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(2 * c, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.net(x.transpose(1, 2))  # (B, C, T)
        return self.head(self.drop(torch.cat([h.mean(dim=2), h.amax(dim=2)], dim=1)))


class TransformerClassifier(nn.Module):
    """Transformer encoder: linear projection, learned positional embedding, self attention layers, mean pooling, linear head."""

    def __init__(
        self, feature_dim: int, num_classes: int, hidden: int = 128, layers: int = 2, heads: int = 4,
        dropout: float = 0.3, max_len: int = 256,
    ) -> None:
        super().__init__()
        if hidden % heads:
            raise ValueError("hidden must be divisible by heads")
        self.proj = nn.Linear(feature_dim, hidden)
        self.pos = nn.Parameter(torch.zeros(1, max_len, hidden))
        nn.init.normal_(self.pos, std=1 / math.sqrt(hidden))
        layer = nn.TransformerEncoderLayer(hidden, heads, dim_feedforward=hidden * 2, dropout=dropout, batch_first=True)
        self.encoder = nn.TransformerEncoder(layer, num_layers=layers)
        self.norm = nn.LayerNorm(hidden)
        self.head = nn.Linear(hidden, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.shape[1] > self.pos.shape[1]:
            raise ValueError(f"sequence length {x.shape[1]} exceeds the maximum {self.pos.shape[1]}")
        h = self.proj(x) + self.pos[:, : x.shape[1]]
        return self.head(self.norm(self.encoder(h)).mean(dim=1))


def build_model(config: "ModelConfig") -> nn.Module:
    n = len(config.classes)
    if config.arch == "cnn":
        return CNN1DClassifier(config.feature_dim, n, config.hidden, config.dropout)
    if config.arch == "bigru":
        return BiGRUClassifier(config.feature_dim, n, config.hidden, config.layers, config.dropout)
    if config.arch == "transformer":
        return TransformerClassifier(config.feature_dim, n, config.hidden, config.layers, config.heads, config.dropout)
    raise ValueError(f"unknown architecture {config.arch!r}; expected one of {ARCHITECTURES}")
