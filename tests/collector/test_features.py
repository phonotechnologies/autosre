"""Tests for the OTel feature engineering pipeline.

Uses synthetic DataFrames to validate aggregation logic, column naming,
and metadata exclusion without requiring real OTel data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from autosre.collector.features import (
    engineer_log_features,
    engineer_metric_features,
    engineer_trace_features,
    get_feature_columns,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic telemetry DataFrames
# ---------------------------------------------------------------------------


@pytest.fixture()
def metric_df() -> pd.DataFrame:
    """Synthetic metric data: 2 services, 2 metrics, 10 samples each over 2 minutes."""
    rng = np.random.default_rng(42)
    rows = []
    base = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
    for svc in ["frontend", "backend"]:
        for metric in ["cpu_usage", "memory_bytes"]:
            for i in range(10):
                rows.append(
                    {
                        "service": svc,
                        "metric_name": metric,
                        "timestamp": base + pd.Timedelta(seconds=i * 10),
                        "value": rng.uniform(0.1, 100.0),
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture()
def trace_df() -> pd.DataFrame:
    """Synthetic trace data: 2 services, 20 spans, some with errors."""
    rng = np.random.default_rng(42)
    rows = []
    base = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
    for svc in ["frontend", "backend"]:
        for i in range(10):
            trace_id = f"trace_{svc}_{i // 3}"
            rows.append(
                {
                    "trace_id": trace_id,
                    "span_id": f"span_{svc}_{i}",
                    "parent_span_id": "" if i % 3 == 0 else f"span_{svc}_{i - 1}",
                    "service": svc,
                    "operation": f"GET /api/{svc}",
                    "start_time": base + pd.Timedelta(seconds=i * 5),
                    "duration_us": int(rng.uniform(100, 50000)),
                    "status_code": "500" if i == 7 else "200",
                    "kind": 1,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture()
def log_df() -> pd.DataFrame:
    """Synthetic log data: 2 services, 20 log records with mixed severity."""
    rows = []
    base = pd.Timestamp("2026-01-01T00:00:00", tz="UTC")
    severities = ["INFO", "INFO", "WARN", "ERROR", "INFO", "INFO", "INFO", "INFO", "FATAL", "INFO"]
    bodies = [
        "Request processed",
        "Cache hit",
        "Warning: high latency detected",
        "Error: connection refused",
        "Request processed",
        "Healthy",
        "Request processed",
        "Cache miss",
        "Fatal: out of memory panic",
        "Request processed",
    ]
    for svc in ["frontend", "backend"]:
        for i in range(10):
            rows.append(
                {
                    "service": svc,
                    "timestamp": base + pd.Timedelta(seconds=i * 5),
                    "severity": severities[i],
                    "body": bodies[i],
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests: engineer_metric_features
# ---------------------------------------------------------------------------


class TestMetricFeatures:
    def test_produces_expected_columns(self, metric_df: pd.DataFrame) -> None:
        result = engineer_metric_features(metric_df, window_minutes=1)
        assert "timestamp" in result.columns
        assert "service" in result.columns
        # Should have mean/std/max for each metric
        for metric in ["cpu_usage", "memory_bytes"]:
            for stat in ["mean", "std", "max"]:
                col = f"{metric}_{stat}"
                assert col in result.columns, f"Missing column {col}"

    def test_groups_by_service(self, metric_df: pd.DataFrame) -> None:
        result = engineer_metric_features(metric_df, window_minutes=1)
        services = set(result["service"].unique())
        assert services == {"frontend", "backend"}

    def test_window_aggregation(self, metric_df: pd.DataFrame) -> None:
        result = engineer_metric_features(metric_df, window_minutes=1)
        # 10 samples over ~90 seconds = 2 one-minute windows per service
        # (seconds 0-50 in first window, 60-90 in second)
        for svc in ["frontend", "backend"]:
            svc_rows = result[result["service"] == svc]
            assert len(svc_rows) == 2, f"Expected 2 windows for {svc}, got {len(svc_rows)}"

    def test_no_nan_values(self, metric_df: pd.DataFrame) -> None:
        result = engineer_metric_features(metric_df, window_minutes=1)
        feature_cols = get_feature_columns(result)
        assert not result[feature_cols].isna().any().any()

    def test_empty_input(self) -> None:
        empty = pd.DataFrame(columns=["service", "metric_name", "timestamp", "value"])
        result = engineer_metric_features(empty)
        assert len(result) == 0

    def test_custom_window_size(self, metric_df: pd.DataFrame) -> None:
        result = engineer_metric_features(metric_df, window_minutes=5)
        # All 10 samples (0-90s) fit in a single 5-min window per service
        for svc in ["frontend", "backend"]:
            svc_rows = result[result["service"] == svc]
            assert len(svc_rows) == 1


# ---------------------------------------------------------------------------
# Tests: engineer_trace_features
# ---------------------------------------------------------------------------


class TestTraceFeatures:
    def test_produces_expected_columns(self, trace_df: pd.DataFrame) -> None:
        result = engineer_trace_features(trace_df, window_minutes=1)
        expected = [
            "timestamp",
            "service",
            "span_count",
            "trace_count",
            "p50_duration",
            "p95_duration",
            "p99_duration",
            "mean_duration",
            "std_duration",
            "max_duration",
            "error_span_count",
            "error_span_rate",
            "duration_cv",
        ]
        for col in expected:
            assert col in result.columns, f"Missing column {col}"

    def test_error_detection(self, trace_df: pd.DataFrame) -> None:
        result = engineer_trace_features(trace_df, window_minutes=5)
        # Each service has 1 span with status 500 (index 7)
        total_errors = result["error_span_count"].sum()
        assert total_errors == 2, f"Expected 2 error spans, got {total_errors}"

    def test_latency_percentile_ordering(self, trace_df: pd.DataFrame) -> None:
        result = engineer_trace_features(trace_df, window_minutes=5)
        for _, row in result.iterrows():
            assert row["p50_duration"] <= row["p95_duration"]
            assert row["p95_duration"] <= row["p99_duration"]

    def test_trace_count_less_than_span_count(self, trace_df: pd.DataFrame) -> None:
        result = engineer_trace_features(trace_df, window_minutes=5)
        for _, row in result.iterrows():
            assert row["trace_count"] <= row["span_count"]

    def test_error_rate_bounded(self, trace_df: pd.DataFrame) -> None:
        result = engineer_trace_features(trace_df, window_minutes=1)
        assert (result["error_span_rate"] >= 0).all()
        assert (result["error_span_rate"] <= 1).all()

    def test_empty_input(self) -> None:
        empty = pd.DataFrame(
            columns=[
                "trace_id",
                "span_id",
                "parent_span_id",
                "service",
                "operation",
                "start_time",
                "duration_us",
                "status_code",
                "kind",
            ]
        )
        result = engineer_trace_features(empty)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Tests: engineer_log_features
# ---------------------------------------------------------------------------


class TestLogFeatures:
    def test_produces_expected_columns(self, log_df: pd.DataFrame) -> None:
        result = engineer_log_features(log_df, window_minutes=1)
        expected = [
            "timestamp",
            "service",
            "log_count",
            "error_count",
            "warn_count",
            "error_rate",
            "log_rate_change",
        ]
        for col in expected:
            assert col in result.columns, f"Missing column {col}"

    def test_error_count(self, log_df: pd.DataFrame) -> None:
        result = engineer_log_features(log_df, window_minutes=5)
        # Each service: index 3 = ERROR "connection refused", index 8 = FATAL "panic"
        for svc in ["frontend", "backend"]:
            svc_errors = result.loc[result["service"] == svc, "error_count"].sum()
            assert svc_errors == 2, f"Expected 2 errors for {svc}, got {svc_errors}"

    def test_warn_count(self, log_df: pd.DataFrame) -> None:
        result = engineer_log_features(log_df, window_minutes=5)
        # Each service: index 2 = WARN "warning"
        for svc in ["frontend", "backend"]:
            svc_warns = result.loc[result["service"] == svc, "warn_count"].sum()
            assert svc_warns == 1, f"Expected 1 warn for {svc}, got {svc_warns}"

    def test_error_rate_bounded(self, log_df: pd.DataFrame) -> None:
        result = engineer_log_features(log_df, window_minutes=1)
        assert (result["error_rate"] >= 0).all()
        assert (result["error_rate"] <= 1).all()

    def test_rate_change_clipped(self, log_df: pd.DataFrame) -> None:
        result = engineer_log_features(log_df, window_minutes=1)
        assert (result["log_rate_change"] >= -10).all()
        assert (result["log_rate_change"] <= 10).all()

    def test_empty_input(self) -> None:
        empty = pd.DataFrame(columns=["service", "timestamp", "severity", "body"])
        result = engineer_log_features(empty)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Tests: get_feature_columns
# ---------------------------------------------------------------------------


class TestGetFeatureColumns:
    def test_excludes_metadata(self, metric_df: pd.DataFrame) -> None:
        result = engineer_metric_features(metric_df, window_minutes=1)
        feature_cols = get_feature_columns(result)
        for meta in ["timestamp", "service"]:
            assert meta not in feature_cols

    def test_includes_numeric_features(self, metric_df: pd.DataFrame) -> None:
        result = engineer_metric_features(metric_df, window_minutes=1)
        feature_cols = get_feature_columns(result)
        assert len(feature_cols) > 0
        # All returned columns should be numeric
        for col in feature_cols:
            assert np.issubdtype(result[col].dtype, np.number), f"{col} is not numeric"

    def test_excludes_label_column(self, trace_df: pd.DataFrame) -> None:
        result = engineer_trace_features(trace_df, window_minutes=1)
        result["label"] = 0  # simulate labeling
        feature_cols = get_feature_columns(result)
        assert "label" not in feature_cols

    def test_sorted_output(self, metric_df: pd.DataFrame) -> None:
        result = engineer_metric_features(metric_df, window_minutes=1)
        feature_cols = get_feature_columns(result)
        assert feature_cols == sorted(feature_cols)

    def test_log_features_columns(self, log_df: pd.DataFrame) -> None:
        result = engineer_log_features(log_df, window_minutes=1)
        feature_cols = get_feature_columns(result)
        assert "log_count" in feature_cols
        assert "error_count" in feature_cols
        assert "error_rate" in feature_cols


# ---------------------------------------------------------------------------
# Tests: parser integration (round-trip)
# ---------------------------------------------------------------------------


class TestParserRoundTrip:
    """Verify that parsed OTLP data feeds cleanly into feature engineering."""

    def test_metrics_round_trip(self) -> None:
        from autosre.collector.parser import parse_otlp_metrics

        otlp = {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "cart"}},
                        ]
                    },
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "cpu_usage",
                                    "gauge": {
                                        "dataPoints": [
                                            {
                                                "timeUnixNano": "1704067200000000000",
                                                "asDouble": 0.42,
                                            },
                                            {
                                                "timeUnixNano": "1704067260000000000",
                                                "asDouble": 0.55,
                                            },
                                        ]
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        parsed = parse_otlp_metrics(otlp)
        assert len(parsed) == 2
        features = engineer_metric_features(parsed, window_minutes=1)
        assert len(features) == 2
        assert "cpu_usage_mean" in features.columns

    def test_traces_round_trip(self) -> None:
        from autosre.collector.parser import parse_otlp_traces

        otlp = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "checkout"}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "abc123",
                                    "spanId": "span1",
                                    "parentSpanId": "",
                                    "name": "POST /checkout",
                                    "startTimeUnixNano": "1704067200000000000",
                                    "endTimeUnixNano": "1704067200050000000",
                                    "status": {"code": 0},
                                    "kind": 1,
                                    "attributes": [],
                                },
                                {
                                    "traceId": "abc123",
                                    "spanId": "span2",
                                    "parentSpanId": "span1",
                                    "name": "SELECT orders",
                                    "startTimeUnixNano": "1704067200010000000",
                                    "endTimeUnixNano": "1704067200030000000",
                                    "status": {"code": 2},
                                    "kind": 3,
                                    "attributes": [],
                                },
                            ],
                        }
                    ],
                }
            ],
        }
        parsed = parse_otlp_traces(otlp)
        assert len(parsed) == 2
        features = engineer_trace_features(parsed, window_minutes=1)
        assert len(features) == 1
        assert features.iloc[0]["span_count"] == 2
        assert features.iloc[0]["trace_count"] == 1
        assert features.iloc[0]["error_span_count"] == 1  # status code "2" = gRPC ERROR

    def test_logs_round_trip(self) -> None:
        from autosre.collector.parser import parse_otlp_logs

        otlp = {
            "resourceLogs": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "payment"}},
                        ]
                    },
                    "scopeLogs": [
                        {
                            "logRecords": [
                                {
                                    "timeUnixNano": "1704067200000000000",
                                    "severityText": "INFO",
                                    "body": {"stringValue": "Payment processed"},
                                    "attributes": [],
                                },
                                {
                                    "timeUnixNano": "1704067201000000000",
                                    "severityText": "ERROR",
                                    "body": {"stringValue": "Connection timeout exception"},
                                    "attributes": [],
                                },
                            ],
                        }
                    ],
                }
            ],
        }
        parsed = parse_otlp_logs(otlp)
        assert len(parsed) == 2
        features = engineer_log_features(parsed, window_minutes=1)
        assert len(features) == 1
        assert features.iloc[0]["log_count"] == 2
        assert features.iloc[0]["error_count"] == 1
