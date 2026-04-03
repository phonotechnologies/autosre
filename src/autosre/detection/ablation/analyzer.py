"""Feature ablation analysis for anomaly detection models.

Paper 5 discovery: mean-only metrics (12 features) achieve AUC=0.964,
outperforming the full 300+ feature set. This module systematically removes
feature groups and measures the AUC impact to identify which telemetry
signals and feature categories actually matter.

Usage:
    analyzer = FeatureAblationAnalyzer(detector, X_train, X_test, y_test)
    results = analyzer.run_ablation(feature_groups)
    droppable = analyzer.recommend_features(min_auc_delta=0.01)
"""

from __future__ import annotations

import copy
import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from autosre.detection.models.base import BaseDetector

logger = logging.getLogger(__name__)


class FeatureAblationAnalyzer:
    """Systematically remove feature categories and measure AUC impact.

    Paper 5 finding: mean-only metrics achieve AUC=0.964, beating full features.
    This validates that finding by running leave-one-group-out ablation and
    reporting which groups can be safely dropped.
    """

    def __init__(
        self,
        detector: BaseDetector,
        X_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ):
        self._detector = detector
        self._X_train = X_train
        self._X_test = X_test
        self._y_test = y_test
        self._baseline_auc: float | None = None
        self._last_results: pd.DataFrame | None = None

    @property
    def baseline_auc(self) -> float:
        """AUC with all features included. Computed on first access."""
        if self._baseline_auc is None:
            self._baseline_auc = self._evaluate(self._X_train, self._X_test)
        return self._baseline_auc

    def run_ablation(self, feature_groups: dict[str, list[int]]) -> pd.DataFrame:
        """Remove each feature group, retrain, measure AUC.

        Args:
            feature_groups: mapping from group name to list of column indices.
                Example: {"mean_metrics": [0,1,2], "p99_metrics": [3,4,5],
                          "trace_spans": [6,7,8], "log_counts": [9,10]}

        Returns:
            DataFrame with columns:
                group_name: name of the removed feature group
                n_features_removed: how many features were in the group
                auc_with: baseline AUC (all features)
                auc_without: AUC after removing this group
                delta: auc_without - auc_with (positive means removing helped)
        """
        baseline = self.baseline_auc
        all_cols = set(range(self._X_train.shape[1]))
        results: list[dict[str, Any]] = []

        for group_name, col_indices in feature_groups.items():
            keep_cols = sorted(all_cols - set(col_indices))
            if not keep_cols:
                logger.warning(
                    "Skipping group '%s': removing it would leave zero features", group_name
                )
                continue

            X_train_ablated = self._X_train[:, keep_cols]
            X_test_ablated = self._X_test[:, keep_cols]

            try:
                auc_without = self._evaluate(X_train_ablated, X_test_ablated)
            except Exception:
                logger.exception("Ablation failed for group '%s'", group_name)
                auc_without = 0.0

            results.append(
                {
                    "group_name": group_name,
                    "n_features_removed": len(col_indices),
                    "auc_with": baseline,
                    "auc_without": auc_without,
                    "delta": auc_without - baseline,
                }
            )
            logger.info(
                "Ablation [%s]: removed %d features, AUC %.4f -> %.4f (delta=%.4f)",
                group_name,
                len(col_indices),
                baseline,
                auc_without,
                auc_without - baseline,
            )

        self._last_results = pd.DataFrame(results)
        return self._last_results

    def recommend_features(self, min_auc_delta: float = 0.01) -> list[str]:
        """Return feature groups that can be dropped without significant AUC loss.

        A group is droppable if removing it causes AUC to decrease by less
        than ``min_auc_delta``, or if removing it actually improves AUC.

        Args:
            min_auc_delta: maximum acceptable AUC decrease. Groups with
                delta >= -min_auc_delta are considered droppable.

        Returns:
            List of group names safe to remove, sorted by delta (best first).

        Raises:
            RuntimeError: if run_ablation has not been called yet.
        """
        if self._last_results is None:
            raise RuntimeError("Call run_ablation() before recommend_features()")
        df = self._last_results
        droppable = df[df["delta"] >= -min_auc_delta].sort_values("delta", ascending=False)
        return droppable["group_name"].tolist()

    def _evaluate(self, X_train: np.ndarray, X_test: np.ndarray) -> float:
        """Train a fresh copy of the detector and compute test AUC."""
        detector = copy.deepcopy(self._detector)
        detector.fit(X_train)
        scores = detector.score(X_test)

        if len(scores) < len(self._y_test):
            y_eval = self._y_test[len(self._y_test) - len(scores) :]
        else:
            y_eval = self._y_test

        if len(np.unique(y_eval)) < 2:
            logger.warning("Only one class present in y_test slice, returning AUC=0.5")
            return 0.5

        return float(roc_auc_score(y_eval, scores))
