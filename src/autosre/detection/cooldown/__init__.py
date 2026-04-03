"""Cooldown-aware anomaly detection.

Core differentiator: automatically excludes post-incident recovery periods
from anomaly baselines, preventing cascading false positives.

No existing tool implements this. Research basis: Paper 5 (IEEE Access, 2026).
"""

from autosre.detection.cooldown.exclusion import CooldownManager

__all__ = ["CooldownManager"]
