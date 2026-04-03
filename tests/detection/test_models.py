"""Tests for anomaly detection models."""

import numpy as np
import pytest

from autosre.detection.models import (
    CNN1DAutoencoderDetector,
    IsolationForestDetector,
    LSTMAutoencoderDetector,
    LSTMVAEDetector,
    ModelRegistry,
    OneClassSVMDetector,
    TransformerAutoencoderDetector,
)


@pytest.fixture
def normal_data() -> np.ndarray:
    """Generate synthetic normal data (Gaussian)."""
    rng = np.random.RandomState(42)
    return rng.randn(200, 10).astype(np.float32)


@pytest.fixture
def anomalous_data() -> np.ndarray:
    """Generate synthetic anomalous data (shifted Gaussian)."""
    rng = np.random.RandomState(99)
    return (rng.randn(50, 10) + 5.0).astype(np.float32)


class TestModelRegistry:
    def test_all_models_registered(self):
        names = ModelRegistry.list_models()
        assert "isolation_forest" in names
        assert "ocsvm" in names
        assert "lstm_ae" in names
        assert "transformer_ae" in names
        assert "cnn1d_ae" in names
        assert "lstm_vae" in names

    def test_get_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            ModelRegistry.get("nonexistent")


class TestIsolationForest:
    def test_fit_and_score(self, normal_data, anomalous_data):
        detector = IsolationForestDetector()
        detector.fit(normal_data)
        normal_scores = detector.score(normal_data)
        anomaly_scores = detector.score(anomalous_data)
        assert normal_scores.shape == (200,)
        assert anomaly_scores.shape == (50,)
        assert 0.0 <= normal_scores.min() <= normal_scores.max() <= 1.0
        assert anomaly_scores.mean() > normal_scores.mean()

    def test_predict(self, normal_data):
        detector = IsolationForestDetector()
        detector.fit(normal_data)
        preds = detector.predict(normal_data, threshold=0.5)
        assert set(np.unique(preds)).issubset({0, 1})


class TestOneClassSVM:
    def test_fit_and_score(self, normal_data, anomalous_data):
        detector = OneClassSVMDetector()
        detector.fit(normal_data)
        normal_scores = detector.score(normal_data)
        anomaly_scores = detector.score(anomalous_data)
        assert normal_scores.shape == (200,)
        assert anomaly_scores.mean() > normal_scores.mean()


class TestLSTMAutoencoder:
    def test_fit_and_score(self, normal_data):
        detector = LSTMAutoencoderDetector(
            n_features=10,
            hidden_dim=16,
            n_layers=1,
            epochs=2,
            seq_length=10,
        )
        detector.fit(normal_data)
        scores = detector.score(normal_data)
        assert len(scores) > 0
        assert 0.0 <= scores.min() <= scores.max() <= 1.0


class TestTransformerAutoencoder:
    def test_fit_and_score(self, normal_data):
        detector = TransformerAutoencoderDetector(
            n_features=10,
            d_model=16,
            nhead=2,
            n_layers=1,
            epochs=2,
            seq_length=10,
        )
        detector.fit(normal_data)
        scores = detector.score(normal_data)
        assert len(scores) > 0


class TestCNN1DAutoencoder:
    def test_fit_and_score(self, normal_data):
        detector = CNN1DAutoencoderDetector(
            n_features=10,
            filters=16,
            n_layers=1,
            epochs=2,
            seq_length=10,
        )
        detector.fit(normal_data)
        scores = detector.score(normal_data)
        assert len(scores) > 0


class TestLSTMVAE:
    def test_fit_and_score(self, normal_data):
        detector = LSTMVAEDetector(
            n_features=10,
            hidden_dim=16,
            n_layers=1,
            latent_dim=8,
            epochs=2,
            seq_length=10,
        )
        detector.fit(normal_data)
        scores = detector.score(normal_data)
        assert len(scores) > 0
