"""Temporal cooldown exclusion for anomaly detection.

Ported and generalized from Paper 5's mark_cooldown_windows(). The research
version operates on fixed 10-minute blocks (5 min fault + 5 min recovery).
This production version supports configurable cooldown durations per signal
and dynamic incident boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


@dataclass
class CooldownWindow:
    """A single cooldown exclusion window."""

    signal: str
    start: datetime
    end: datetime
    incident_id: str | None = None

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def contains(self, timestamp: datetime) -> bool:
        return self.start <= timestamp < self.end


@dataclass
class CooldownConfig:
    """Configuration for cooldown behavior."""

    enabled: bool = True
    default_duration: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    per_signal_duration: dict[str, timedelta] = field(default_factory=dict)

    def get_duration(self, signal: str) -> timedelta:
        return self.per_signal_duration.get(signal, self.default_duration)


class CooldownManager:
    """Manages cooldown windows for anomaly detection.

    Tracks active incidents and their recovery periods. Data points
    falling within cooldown windows are excluded from:
    1. Training data (prevents learning recovery patterns as normal)
    2. Evaluation (prevents false positive alerts during recovery)
    """

    def __init__(self, config: CooldownConfig | None = None):
        self.config = config or CooldownConfig()
        self._windows: list[CooldownWindow] = []

    def register_incident(
        self,
        signal: str,
        incident_end: datetime,
        incident_id: str | None = None,
    ) -> CooldownWindow:
        """Register an incident and create a cooldown window starting at incident_end."""
        duration = self.config.get_duration(signal)
        window = CooldownWindow(
            signal=signal,
            start=incident_end,
            end=incident_end + duration,
            incident_id=incident_id,
        )
        self._windows.append(window)
        return window

    def is_in_cooldown(self, signal: str, timestamp: datetime) -> bool:
        """Check if a timestamp falls within any cooldown window for a signal."""
        if not self.config.enabled:
            return False
        return any(w.signal == signal and w.contains(timestamp) for w in self._windows)

    def apply_mask(
        self, df: pd.DataFrame, signal: str, timestamp_col: str = "timestamp"
    ) -> pd.Series:
        """Return boolean mask where True = in cooldown (should be excluded)."""
        if not self.config.enabled or not self._windows:
            return pd.Series(False, index=df.index)

        mask = pd.Series(False, index=df.index)
        signal_windows = [w for w in self._windows if w.signal == signal]
        for window in signal_windows:
            mask |= (df[timestamp_col] >= window.start) & (df[timestamp_col] < window.end)
        return mask

    def filter_training_data(
        self,
        X: np.ndarray,
        timestamps: np.ndarray,
        signal: str,
    ) -> np.ndarray:
        """Remove cooldown periods from training data."""
        if not self.config.enabled or not self._windows:
            return X

        keep_mask = np.ones(len(X), dtype=bool)
        signal_windows = [w for w in self._windows if w.signal == signal]
        for window in signal_windows:
            in_window = (timestamps >= np.datetime64(window.start)) & (
                timestamps < np.datetime64(window.end)
            )
            keep_mask &= ~in_window
        return X[keep_mask]

    def mark_cooldown_windows_paper5(self, df: pd.DataFrame) -> pd.Series:
        """Paper 5 compatible cooldown marking for research reproducibility.

        Each fault injection run is 10 minutes: 5 min active + 5 min recovery.
        Groups by (rep, fault_type), identifies 10-sample blocks, marks
        last 5 of each block as cooldown.
        """
        is_cooldown = pd.Series(False, index=df.index)
        fi_mask = df["label"] == 1 if "label" in df.columns else pd.Series(False, index=df.index)
        if fi_mask.sum() == 0:
            return is_cooldown

        group_cols = [c for c in ["rep", "fault_type"] if c in df.columns]
        if not group_cols:
            return is_cooldown

        fi_df = df[fi_mask]
        for _, group in fi_df.groupby(group_cols):
            sorted_group = group.sort_values("timestamp") if "timestamp" in group.columns else group
            indices = sorted_group.index.tolist()
            n = len(indices)
            block_size = 10
            cooldown_size = 5

            for b in range(n // block_size):
                cooldown_start = b * block_size + (block_size - cooldown_size)
                cooldown_indices = indices[cooldown_start : cooldown_start + cooldown_size]
                is_cooldown.loc[cooldown_indices] = True

            remainder_start = (n // block_size) * block_size
            remainder = indices[remainder_start:]
            if len(remainder) > cooldown_size:
                is_cooldown.loc[remainder[-cooldown_size:]] = True

        return is_cooldown

    @property
    def active_windows(self) -> list[CooldownWindow]:
        return list(self._windows)

    def clear(self) -> None:
        self._windows.clear()
