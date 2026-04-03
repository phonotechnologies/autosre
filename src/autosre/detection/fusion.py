"""Late fusion strategies for multi-signal anomaly detection.

Ported from Paper 5 (IEEE Access, 2026): combines per-signal anomaly scores
into a single fused score. Four strategies mirror the paper's evaluation
(training.py lines 822-856).

Typical usage:
    scores = {"metrics": m_scores, "traces": t_scores, "logs": l_scores}
    fused = SignalFusion.max_fusion(scores)
"""

from __future__ import annotations

import numpy as np


class SignalFusion:
    """Late fusion of anomaly scores from multiple OTel signals.

    All methods accept a dict mapping signal name to a 1D array of anomaly
    scores in [0, 1]. All input arrays must have the same length.
    """

    @staticmethod
    def _validate(scores: dict[str, np.ndarray]) -> None:
        if not scores:
            raise ValueError("scores dict must not be empty")
        lengths = {name: len(arr) for name, arr in scores.items()}
        unique_lengths = set(lengths.values())
        if len(unique_lengths) > 1:
            raise ValueError(f"All score arrays must have equal length, got: {lengths}")

    @staticmethod
    def max_fusion(scores: dict[str, np.ndarray]) -> np.ndarray:
        """Anomaly if ANY signal detects.

        Takes the element-wise maximum across all signals. This is the most
        sensitive strategy: a single high-scoring signal triggers detection.
        """
        SignalFusion._validate(scores)
        stacked = np.stack(list(scores.values()), axis=0)
        return np.max(stacked, axis=0)

    @staticmethod
    def average_fusion(scores: dict[str, np.ndarray]) -> np.ndarray:
        """Mean of all signal scores.

        Simple unweighted average. Works well when signals have comparable
        score distributions and no single signal dominates.
        """
        SignalFusion._validate(scores)
        stacked = np.stack(list(scores.values()), axis=0)
        return np.mean(stacked, axis=0)

    @staticmethod
    def weighted_fusion(
        scores: dict[str, np.ndarray],
        weights: dict[str, float],
    ) -> np.ndarray:
        """Weighted average of signal scores.

        Weights are normalized to sum to 1.0 internally. Signals present in
        scores but missing from weights receive weight 0.0. This allows
        prioritizing signals with higher per-signal AUC (e.g., traces
        weight=0.5, metrics weight=0.3, logs weight=0.2 based on Paper 5
        AUC results).
        """
        SignalFusion._validate(scores)
        signal_names = list(scores.keys())
        raw_weights = np.array([weights.get(name, 0.0) for name in signal_names])
        total = raw_weights.sum()
        if total <= 0:
            raise ValueError("Weights must sum to a positive value")
        normalized = raw_weights / total

        stacked = np.stack([scores[name] for name in signal_names], axis=0)
        return np.einsum("s,st->t", normalized, stacked)

    @staticmethod
    def majority_vote(
        scores: dict[str, np.ndarray],
        thresholds: dict[str, float],
    ) -> np.ndarray:
        """Anomaly if >= 2 of 3 signals exceed their thresholds.

        Returns binary array (0 or 1). Each signal is independently
        thresholded, then a majority vote determines the final decision.
        For N signals, the quorum is ceil(N / 2).
        """
        SignalFusion._validate(scores)
        n_signals = len(scores)
        quorum = (n_signals + 1) // 2  # ceil(N/2)

        votes = []
        for name, arr in scores.items():
            t = thresholds.get(name, 0.5)
            votes.append((arr >= t).astype(np.float64))

        vote_sum = np.sum(np.stack(votes, axis=0), axis=0)
        return (vote_sum >= quorum).astype(np.float64)
