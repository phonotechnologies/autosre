"""Base detector interface and model registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import joblib
import numpy as np


class BaseDetector(ABC):
    """Abstract base class for all anomaly detectors."""

    name: str = "base"

    @abstractmethod
    def fit(self, X_normal: np.ndarray, X_val: np.ndarray | None = None) -> None:
        """Train on normal data only (semi-supervised)."""

    @abstractmethod
    def score(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly scores in [0, 1]. Higher = more anomalous."""

    @abstractmethod
    def get_params(self) -> dict[str, Any]:
        """Return current hyperparameters."""

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Binary anomaly predictions."""
        return (self.score(X) >= threshold).astype(int)

    def save(self, path: Path) -> None:
        """Serialize detector to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> BaseDetector:
        """Load detector from disk."""
        return joblib.load(path)


class ModelRegistry:
    """Registry of available detection models."""

    _models: dict[str, type[BaseDetector]] = {}

    @classmethod
    def register(cls, model_cls: type[BaseDetector]) -> type[BaseDetector]:
        cls._models[model_cls.name] = model_cls
        return model_cls

    @classmethod
    def get(cls, name: str) -> type[BaseDetector]:
        if name not in cls._models:
            available = ", ".join(sorted(cls._models.keys()))
            raise ValueError(f"Unknown model '{name}'. Available: {available}")
        return cls._models[name]

    @classmethod
    def list_models(cls) -> list[str]:
        return sorted(cls._models.keys())

    @classmethod
    def create_all(cls, n_features: int, **kwargs: Any) -> dict[str, BaseDetector]:
        """Create instances of all registered models."""
        instances = {}
        for name, model_cls in cls._models.items():
            try:
                instances[name] = model_cls(n_features=n_features, **kwargs)
            except TypeError:
                instances[name] = model_cls(**kwargs)
        return instances
