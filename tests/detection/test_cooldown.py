"""Tests for cooldown exclusion logic."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from autosre.detection.cooldown.exclusion import CooldownConfig, CooldownManager


@pytest.fixture
def manager() -> CooldownManager:
    config = CooldownConfig(
        enabled=True,
        default_duration=timedelta(minutes=10),
    )
    return CooldownManager(config)


class TestCooldownManager:
    def test_register_incident(self, manager):
        incident_end = datetime(2026, 4, 3, 12, 0, 0)
        window = manager.register_incident("metrics", incident_end, "inc-001")
        assert window.signal == "metrics"
        assert window.start == incident_end
        assert window.end == incident_end + timedelta(minutes=10)

    def test_is_in_cooldown(self, manager):
        incident_end = datetime(2026, 4, 3, 12, 0, 0)
        manager.register_incident("metrics", incident_end)

        assert manager.is_in_cooldown("metrics", datetime(2026, 4, 3, 12, 5, 0))
        assert not manager.is_in_cooldown("metrics", datetime(2026, 4, 3, 12, 15, 0))
        assert not manager.is_in_cooldown("traces", datetime(2026, 4, 3, 12, 5, 0))

    def test_disabled_cooldown(self):
        config = CooldownConfig(enabled=False)
        manager = CooldownManager(config)
        manager.register_incident("metrics", datetime(2026, 4, 3, 12, 0, 0))
        assert not manager.is_in_cooldown("metrics", datetime(2026, 4, 3, 12, 5, 0))

    def test_apply_mask(self, manager):
        incident_end = datetime(2026, 4, 3, 12, 0, 0)
        manager.register_incident("metrics", incident_end)

        timestamps = [incident_end + timedelta(minutes=i) for i in range(-5, 15)]
        df = pd.DataFrame({"timestamp": timestamps, "value": range(20)})
        mask = manager.apply_mask(df, "metrics")

        assert mask.sum() == 10
        assert not mask.iloc[0]
        assert mask.iloc[5]

    def test_filter_training_data(self, manager):
        incident_end = datetime(2026, 4, 3, 12, 0, 0)
        manager.register_incident("metrics", incident_end)

        timestamps = np.array(
            [np.datetime64(incident_end + timedelta(minutes=i)) for i in range(-5, 15)]
        )
        X = np.random.randn(20, 5)
        X_filtered = manager.filter_training_data(X, timestamps, "metrics")
        assert len(X_filtered) == 10

    def test_paper5_cooldown(self):
        manager = CooldownManager()
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-01-01", periods=20, freq="1min"),
                "label": [1] * 10 + [0] * 10,
                "rep": [1] * 10 + [0] * 10,
                "fault_type": ["cpu_stress"] * 10 + ["normal"] * 10,
                "value": range(20),
            }
        )
        mask = manager.mark_cooldown_windows_paper5(df)
        assert mask.sum() == 5
        assert mask.iloc[5:10].all()

    def test_per_signal_duration(self):
        config = CooldownConfig(
            per_signal_duration={
                "metrics": timedelta(minutes=5),
                "traces": timedelta(minutes=15),
            }
        )
        manager = CooldownManager(config)
        t = datetime(2026, 4, 3, 12, 0, 0)

        manager.register_incident("metrics", t)
        manager.register_incident("traces", t)

        assert manager.is_in_cooldown("metrics", t + timedelta(minutes=3))
        assert not manager.is_in_cooldown("metrics", t + timedelta(minutes=7))
        assert manager.is_in_cooldown("traces", t + timedelta(minutes=12))
