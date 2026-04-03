"""Tests for multi-signal late fusion strategies."""

import numpy as np
import pytest

from autosre.detection.fusion import SignalFusion


@pytest.fixture
def three_signal_scores() -> dict[str, np.ndarray]:
    """Synthetic scores for metrics, traces, logs (100 timesteps)."""
    rng = np.random.RandomState(42)
    return {
        "metrics": rng.uniform(0.0, 0.3, size=100),
        "traces": rng.uniform(0.0, 0.5, size=100),
        "logs": rng.uniform(0.0, 0.2, size=100),
    }


@pytest.fixture
def scores_with_spike() -> dict[str, np.ndarray]:
    """One signal has a clear anomaly spike at index 50."""
    metrics = np.full(100, 0.1)
    traces = np.full(100, 0.1)
    logs = np.full(100, 0.1)
    traces[50] = 0.95  # anomaly spike
    return {"metrics": metrics, "traces": traces, "logs": logs}


class TestMaxFusion:
    def test_shape(self, three_signal_scores):
        result = SignalFusion.max_fusion(three_signal_scores)
        assert result.shape == (100,)

    def test_max_picks_highest(self, scores_with_spike):
        result = SignalFusion.max_fusion(scores_with_spike)
        assert result[50] == pytest.approx(0.95)
        assert result[0] == pytest.approx(0.1)

    def test_always_gte_average(self, three_signal_scores):
        max_result = SignalFusion.max_fusion(three_signal_scores)
        avg_result = SignalFusion.average_fusion(three_signal_scores)
        assert np.all(max_result >= avg_result - 1e-10)


class TestAverageFusion:
    def test_shape(self, three_signal_scores):
        result = SignalFusion.average_fusion(three_signal_scores)
        assert result.shape == (100,)

    def test_mean_of_constants(self):
        scores = {
            "a": np.array([0.2, 0.4, 0.6]),
            "b": np.array([0.4, 0.6, 0.8]),
        }
        result = SignalFusion.average_fusion(scores)
        np.testing.assert_allclose(result, [0.3, 0.5, 0.7])

    def test_single_signal(self):
        scores = {"only": np.array([0.1, 0.9, 0.5])}
        result = SignalFusion.average_fusion(scores)
        np.testing.assert_allclose(result, [0.1, 0.9, 0.5])


class TestWeightedFusion:
    def test_equal_weights_matches_average(self, three_signal_scores):
        weights = {"metrics": 1.0, "traces": 1.0, "logs": 1.0}
        weighted = SignalFusion.weighted_fusion(three_signal_scores, weights)
        average = SignalFusion.average_fusion(three_signal_scores)
        np.testing.assert_allclose(weighted, average, atol=1e-10)

    def test_single_weight_selects_signal(self):
        scores = {
            "a": np.array([0.1, 0.2]),
            "b": np.array([0.9, 0.8]),
        }
        weights = {"a": 0.0, "b": 1.0}
        result = SignalFusion.weighted_fusion(scores, weights)
        np.testing.assert_allclose(result, [0.9, 0.8])

    def test_weights_are_normalized(self):
        scores = {
            "a": np.array([1.0]),
            "b": np.array([0.0]),
        }
        # Weights 3:1, so result = 3/4 * 1.0 + 1/4 * 0.0 = 0.75
        weights = {"a": 3.0, "b": 1.0}
        result = SignalFusion.weighted_fusion(scores, weights)
        np.testing.assert_allclose(result, [0.75])

    def test_missing_weight_defaults_zero(self):
        scores = {"a": np.array([1.0]), "b": np.array([0.0])}
        weights = {"a": 1.0}  # b missing, defaults to 0
        result = SignalFusion.weighted_fusion(scores, weights)
        np.testing.assert_allclose(result, [1.0])

    def test_all_zero_weights_raises(self):
        scores = {"a": np.array([0.5])}
        with pytest.raises(ValueError, match="positive"):
            SignalFusion.weighted_fusion(scores, {"a": 0.0})


class TestMajorityVote:
    def test_two_of_three_triggers(self, scores_with_spike):
        # Only traces spikes, so majority vote should NOT fire at index 50
        # (only 1 of 3 exceeds threshold).
        thresholds = {"metrics": 0.5, "traces": 0.5, "logs": 0.5}
        result = SignalFusion.majority_vote(scores_with_spike, thresholds)
        assert result[50] == 0.0  # only 1 signal exceeds

    def test_majority_fires_when_two_exceed(self):
        scores = {
            "a": np.array([0.8]),
            "b": np.array([0.9]),
            "c": np.array([0.1]),
        }
        thresholds = {"a": 0.5, "b": 0.5, "c": 0.5}
        result = SignalFusion.majority_vote(scores, thresholds)
        assert result[0] == 1.0

    def test_all_below_threshold(self):
        scores = {
            "a": np.array([0.1, 0.2]),
            "b": np.array([0.1, 0.3]),
        }
        thresholds = {"a": 0.5, "b": 0.5}
        result = SignalFusion.majority_vote(scores, thresholds)
        np.testing.assert_array_equal(result, [0.0, 0.0])

    def test_two_signals_both_exceed(self):
        scores = {
            "a": np.array([0.8]),
            "b": np.array([0.9]),
        }
        thresholds = {"a": 0.5, "b": 0.5}
        result = SignalFusion.majority_vote(scores, thresholds)
        assert result[0] == 1.0  # 2/2 = quorum of 1

    def test_default_threshold(self):
        scores = {"a": np.array([0.6]), "b": np.array([0.6])}
        # No thresholds provided, defaults to 0.5 for both.
        result = SignalFusion.majority_vote(scores, {})
        assert result[0] == 1.0


class TestValidation:
    def test_empty_dict_raises(self):
        with pytest.raises(ValueError, match="empty"):
            SignalFusion.max_fusion({})

    def test_mismatched_lengths_raises(self):
        scores = {
            "a": np.array([0.1, 0.2]),
            "b": np.array([0.1]),
        }
        with pytest.raises(ValueError, match="equal length"):
            SignalFusion.average_fusion(scores)
