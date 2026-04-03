"""Classical (point-in-time) anomaly detection models.

Ported from Paper 5: "Evaluating ML-based anomaly detection on unified
OpenTelemetry telemetry" (IEEE Access, 2026).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import OneClassSVM

from autosre.detection.models.base import BaseDetector, ModelRegistry


@ModelRegistry.register
class IsolationForestDetector(BaseDetector):
    """Isolation Forest anomaly detector.

    Paper 5 results: best on logs (F1=0.579, AUC=0.640).
    """

    name = "isolation_forest"

    def __init__(
        self,
        n_estimators: int = 200,
        contamination: float = 0.05,
        max_features: float = 1.0,
        max_samples: float = 1.0,
        **_: Any,
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_features = max_features
        self.max_samples = max_samples
        self._model: IsolationForest | None = None

    def fit(self, X_normal: np.ndarray, X_val: np.ndarray | None = None) -> None:
        n_samples = max(1, int(len(X_normal) * self.max_samples))
        self._model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            max_features=self.max_features,
            max_samples=min(n_samples, len(X_normal)),
            random_state=42,
            n_jobs=-1,
        )
        self._model.fit(X_normal)

    def score(self, X: np.ndarray) -> np.ndarray:
        assert self._model is not None, "Model not fitted. Call fit() first."
        raw = self._model.decision_function(X)
        return MinMaxScaler().fit_transform(-raw.reshape(-1, 1)).ravel()

    def get_params(self) -> dict[str, Any]:
        return {
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "max_features": self.max_features,
            "max_samples": self.max_samples,
        }


@ModelRegistry.register
class OneClassSVMDetector(BaseDetector):
    """One-Class SVM anomaly detector.

    Subsamples to 10,000 for training efficiency (Paper 5 pattern).
    """

    name = "ocsvm"

    def __init__(
        self,
        nu: float = 0.05,
        kernel: str = "rbf",
        gamma: str = "scale",
        max_train_samples: int = 10_000,
        **_: Any,
    ):
        self.nu = nu
        self.kernel = kernel
        self.gamma = gamma
        self.max_train_samples = max_train_samples
        self._model: OneClassSVM | None = None

    def fit(self, X_normal: np.ndarray, X_val: np.ndarray | None = None) -> None:
        if len(X_normal) > self.max_train_samples:
            idx = np.random.RandomState(42).choice(
                len(X_normal), self.max_train_samples, replace=False
            )
            X_train = X_normal[idx]
        else:
            X_train = X_normal
        self._model = OneClassSVM(kernel=self.kernel, nu=self.nu, gamma=self.gamma)
        self._model.fit(X_train)

    def score(self, X: np.ndarray) -> np.ndarray:
        assert self._model is not None, "Model not fitted. Call fit() first."
        raw = self._model.decision_function(X)
        return MinMaxScaler().fit_transform(-raw.reshape(-1, 1)).ravel()

    def get_params(self) -> dict[str, Any]:
        return {"nu": self.nu, "kernel": self.kernel, "gamma": self.gamma}
