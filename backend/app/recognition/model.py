import torch
from torch import nn


class BiGRUClassifier(nn.Module):
    """Bidirectional GRU over landmark sequences: (B, T, F) -> class logits (B, C)."""

    def __init__(self, feature_dim: int, num_classes: int, hidden: int = 128, layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.gru = nn.GRU(
            feature_dim, hidden, num_layers=layers, batch_first=True, bidirectional=True,
            dropout=dropout if layers > 1 else 0.0,
        )
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(hidden * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.gru(x)
        return self.head(self.drop(out.mean(dim=1)))
