"""OTel Collector integration: OTLP parsing and feature engineering.

This module provides the ingestion layer that converts raw OpenTelemetry
data (OTLP JSON) into detection-ready feature matrices.

Usage::

    from autosre.collector.parser import parse_otlp_metrics, parse_otlp_traces, parse_otlp_logs
    from autosre.collector.features import (
        engineer_metric_features,
        engineer_trace_features,
        engineer_log_features,
        get_feature_columns,
    )
"""

from autosre.collector.features import (
    engineer_log_features,
    engineer_metric_features,
    engineer_trace_features,
    get_feature_columns,
)
from autosre.collector.parser import (
    parse_otlp_logs,
    parse_otlp_metrics,
    parse_otlp_traces,
)

__all__ = [
    "engineer_log_features",
    "engineer_metric_features",
    "engineer_trace_features",
    "get_feature_columns",
    "parse_otlp_logs",
    "parse_otlp_metrics",
    "parse_otlp_traces",
]
