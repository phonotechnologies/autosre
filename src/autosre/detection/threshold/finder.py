"""Threshold finding strategies from Paper 5.

Three methods:
1. F1-optimal (requires labeled validation data)
2. Percentile-based (unsupervised, uses normal data distribution)
3. Statistical (mean + k*std on normal scores)
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import f1_score


class ThresholdFinder:
    """Automated threshold discovery for anomaly scores."""

    @staticmethod
    def f1_optimal(scores: np.ndarray, y_true: np.ndarray, n_steps: int = 99) -> float:
        """Find threshold that maximizes F1 on labeled validation data."""
        best_f1 = 0.0
        best_t = 0.5
        for t in np.linspace(0.01, 0.99, n_steps):
            preds = (scores >= t).astype(int)
            f1 = f1_score(y_true, preds, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_t = float(t)
        return best_t

    @staticmethod
    def percentile(scores_normal: np.ndarray, percentile: float = 95.0) -> float:
        """Percentile-based threshold on normal data scores. No labels needed."""
        return float(np.percentile(scores_normal, percentile))

    @staticmethod
    def statistical(scores_normal: np.ndarray, k: float = 3.0) -> float:
        """Mean + k*std threshold on normal data scores. No labels needed."""
        return float(np.mean(scores_normal) + k * np.std(scores_normal))

    @staticmethod
    def auto(
        scores: np.ndarray,
        y_true: np.ndarray | None = None,
        scores_normal: np.ndarray | None = None,
    ) -> float:
        """Automatically choose the best threshold strategy.

        Uses F1-optimal if labels available, else percentile on normal scores,
        else defaults to 0.5.
        """
        if y_true is not None and len(y_true) > 0:
            return ThresholdFinder.f1_optimal(scores, y_true)
        if scores_normal is not None and len(scores_normal) > 0:
            return ThresholdFinder.percentile(scores_normal)
        return 0.5
