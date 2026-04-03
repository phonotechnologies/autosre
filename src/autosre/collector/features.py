"""Feature engineering pipeline for OTel telemetry.

Converts parsed telemetry DataFrames (metrics, traces, logs) into
detection-ready feature matrices with 1-minute window aggregations.

Feature engineering approach matches Paper 5 ("Evaluating ML-based anomaly
detection on unified OpenTelemetry telemetry", IEEE Access 2026):

- Metrics: mean, std, max per metric per service per window
- Traces: span_count, trace_count, latency p50/p95/p99, error_rate
- Logs: log_count, error_count, warn_count, error_rate, rate_change
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Columns that are metadata, not numeric features.
# Used by get_feature_columns() to separate features from identifiers.
_METADATA_COLUMNS = frozenset(
    {
        "timestamp",
        "service",
        "label",
        "fault_type",
        "phase",
        "run_id",
        "rep",
        "testbed",
        "window",
    }
)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def engineer_metric_features(
    df: pd.DataFrame,
    window_minutes: int = 1,
) -> pd.DataFrame:
    """Aggregate raw metric samples into per-service windowed features.

    For each (service, window), produces mean/std/max of each metric.
    Expects columns: service, metric_name, timestamp, value.

    Args:
        df: Raw metric DataFrame from ``parse_otlp_metrics`` or Parquet.
        window_minutes: Aggregation window size in minutes.

    Returns:
        DataFrame with columns: timestamp, service, plus one set of
        ``{metric}_mean``, ``{metric}_std``, ``{metric}_max`` columns
        per distinct metric name.
    """
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "service"])

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["window"] = df["timestamp"].dt.floor(f"{window_minutes}min")

    # Need metric_name column to pivot. If not present (single-metric df),
    # use a default name.
    if "metric_name" not in df.columns:
        df["metric_name"] = "metric"

    # Aggregate per (service, window, metric_name)
    agg = (
        df.groupby(["service", "window", "metric_name"])["value"]
        .agg(["mean", "std", "max"])
        .reset_index()
    )
    agg["std"] = agg["std"].fillna(0.0)

    # Pivot metric_name into columns: {metric}_mean, {metric}_std, {metric}_max
    pivoted = agg.pivot_table(
        index=["service", "window"],
        columns="metric_name",
        values=["mean", "std", "max"],
        aggfunc="first",
    )
    # Flatten multi-level column index: ("mean", "cpu_usage") -> "cpu_usage_mean"
    pivoted.columns = [f"{metric}_{stat}" for stat, metric in pivoted.columns]
    pivoted = pivoted.reset_index().rename(columns={"window": "timestamp"})
    pivoted = pivoted.fillna(0.0)
    pivoted = pivoted.sort_values(["service", "timestamp"]).reset_index(drop=True)
    return pivoted


# ---------------------------------------------------------------------------
# Traces
# ---------------------------------------------------------------------------


def engineer_trace_features(
    df: pd.DataFrame,
    window_minutes: int = 1,
) -> pd.DataFrame:
    """Aggregate trace spans into per-service windowed features.

    For each (service, window), produces span_count, trace_count,
    latency percentiles (p50/p95/p99), mean/std/max duration,
    error counts, and duration coefficient of variation.

    Expects columns: service, start_time, duration_us, trace_id,
    span_id, status_code.

    Args:
        df: Parsed trace DataFrame from ``parse_otlp_traces``.
        window_minutes: Aggregation window size in minutes.

    Returns:
        DataFrame with columns: timestamp, service, span_count,
        trace_count, p50_duration, p95_duration, p99_duration,
        mean_duration, std_duration, max_duration, error_span_count,
        error_span_rate, duration_cv.
    """
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "service"])

    df = df.copy()
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["window"] = df["start_time"].dt.floor(f"{window_minutes}min")

    # Error detection: status code 2 (gRPC ERROR), "ERROR", or 5xx HTTP
    df["is_error"] = (
        df["status_code"].astype(str).isin(["2", "ERROR", "500", "502", "503", "504"])
        | df["status_code"].astype(str).str.startswith("5", na=False)
    ).astype(int)

    agg = (
        df.groupby(["service", "window"])
        .agg(
            span_count=("span_id", "count"),
            trace_count=("trace_id", "nunique"),
            p50_duration=("duration_us", lambda x: np.nanpercentile(x, 50)),
            p95_duration=("duration_us", lambda x: np.nanpercentile(x, 95)),
            p99_duration=("duration_us", lambda x: np.nanpercentile(x, 99)),
            mean_duration=("duration_us", "mean"),
            std_duration=("duration_us", "std"),
            max_duration=("duration_us", "max"),
            error_span_count=("is_error", "sum"),
        )
        .reset_index()
    )

    agg["error_span_rate"] = agg["error_span_count"] / agg["span_count"].clip(lower=1)
    agg["duration_cv"] = agg["std_duration"].fillna(0) / agg["mean_duration"].clip(lower=1)

    agg = agg.rename(columns={"window": "timestamp"})
    agg = agg.fillna(0.0)
    agg = agg.sort_values(["service", "timestamp"]).reset_index(drop=True)
    return agg


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


def engineer_log_features(
    df: pd.DataFrame,
    window_minutes: int = 1,
) -> pd.DataFrame:
    """Aggregate log records into per-service windowed features.

    For each (service, window), produces log_count, error_count,
    warn_count, error_rate, and log_rate_change (percent change
    in volume vs. previous window).

    Expects columns: service, timestamp, severity, body.
    Error/warn detection uses both the severity field and body content.

    Args:
        df: Parsed log DataFrame from ``parse_otlp_logs`` or Parquet.
        window_minutes: Aggregation window size in minutes.

    Returns:
        DataFrame with columns: timestamp, service, log_count,
        error_count, warn_count, error_rate, log_rate_change.
    """
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "service"])

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["window"] = df["timestamp"].dt.floor(f"{window_minutes}min")

    # Detect errors from severity text and body content
    severity_lower = df["severity"].astype(str).str.lower()
    body_lower = df.get("body", pd.Series("", index=df.index)).astype(str).str.lower()

    df["is_error"] = (
        severity_lower.isin(["error", "fatal", "critical"])
        | body_lower.str.contains(r"error|exception|fatal|panic|traceback", na=False, regex=True)
    ).astype(int)

    df["is_warn"] = (
        severity_lower.isin(["warn", "warning"])
        | body_lower.str.contains(r"warn|warning", na=False, regex=True)
    ).astype(int)

    agg = (
        df.groupby(["service", "window"])
        .agg(
            log_count=("is_error", "count"),
            error_count=("is_error", "sum"),
            warn_count=("is_warn", "sum"),
        )
        .reset_index()
    )

    agg["error_rate"] = agg["error_count"] / agg["log_count"].clip(lower=1)

    # Log rate change: percent change in volume vs. previous window per service
    agg = agg.sort_values(["service", "window"])
    agg["log_rate_change"] = (
        agg.groupby("service")["log_count"].pct_change().fillna(0.0).clip(-10.0, 10.0)
    )

    agg = agg.rename(columns={"window": "timestamp"})
    agg = agg.reset_index(drop=True)
    return agg


# ---------------------------------------------------------------------------
# Column selection
# ---------------------------------------------------------------------------


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Return numeric feature column names, excluding metadata.

    Identifies columns that are numeric (int or float dtypes) and not
    in the metadata set (timestamp, service, label, fault_type, etc.).

    Args:
        df: Feature DataFrame from any of the engineer_* functions.

    Returns:
        Sorted list of numeric feature column names.
    """
    feature_cols = [
        col
        for col in df.select_dtypes(include=[np.number]).columns
        if col.lower() not in _METADATA_COLUMNS
    ]
    return sorted(feature_cols)
