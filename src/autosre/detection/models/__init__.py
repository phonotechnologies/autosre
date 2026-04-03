"""Six ML models for anomaly detection, ported from Paper 5 (IEEE Access)."""

from autosre.detection.models.base import BaseDetector, ModelRegistry
from autosre.detection.models.classical import (
    IsolationForestDetector,
    OneClassSVMDetector,
)
from autosre.detection.models.deep import (
    CNN1DAutoencoderDetector,
    LSTMAutoencoderDetector,
    LSTMVAEDetector,
    TransformerAutoencoderDetector,
)

__all__ = [
    "BaseDetector",
    "ModelRegistry",
    "IsolationForestDetector",
    "OneClassSVMDetector",
    "LSTMAutoencoderDetector",
    "TransformerAutoencoderDetector",
    "CNN1DAutoencoderDetector",
    "LSTMVAEDetector",
]
