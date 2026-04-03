"""Tests for threshold finding."""

import numpy as np

from autosre.detection.threshold import ThresholdFinder


class TestThresholdFinder:
    def test_f1_optimal(self):
        scores = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
        y_true = np.array([0, 0, 0, 1, 1, 1])
        t = ThresholdFinder.f1_optimal(scores, y_true)
        assert 0.3 < t < 0.8

    def test_percentile(self):
        scores = np.linspace(0, 1, 100)
        t = ThresholdFinder.percentile(scores, 95.0)
        assert 0.9 < t < 1.0

    def test_statistical(self):
        rng = np.random.RandomState(42)
        scores = rng.randn(1000)
        t = ThresholdFinder.statistical(scores, k=3.0)
        assert t > 2.5

    def test_auto_with_labels(self):
        scores = np.array([0.1, 0.9])
        y_true = np.array([0, 1])
        t = ThresholdFinder.auto(scores, y_true=y_true)
        assert 0.0 < t < 1.0

    def test_auto_without_labels(self):
        scores = np.linspace(0, 1, 100)
        t = ThresholdFinder.auto(scores, scores_normal=scores)
        assert 0.9 < t < 1.0

    def test_auto_fallback(self):
        scores = np.array([0.5])
        assert ThresholdFinder.auto(scores) == 0.5
