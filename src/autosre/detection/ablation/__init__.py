"""Feature ablation analysis.

Paper 5 discovery: mean-only metrics (12 features) achieve AUC=0.964,
outperforming the full 300+ feature set. This module quantifies which
telemetry signals and feature categories matter.
"""

from autosre.detection.ablation.analyzer import FeatureAblationAnalyzer

__all__ = ["FeatureAblationAnalyzer"]
