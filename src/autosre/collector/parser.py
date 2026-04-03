"""OTLP JSON data parsers.

Parse OpenTelemetry Protocol (OTLP) JSON exports into tabular DataFrames
suitable for feature engineering. Handles the nested resourceSpans/scopeSpans
structure from OTLP JSON (protobuf-to-JSON encoding).

Ported from Paper 5: infrastructure/sagemaker/preprocessing.py
"""

from __future__ import annotations

from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Attribute helpers
# ---------------------------------------------------------------------------


def _attr_value(attr: dict[str, Any]) -> Any:
    """Extract a typed value from an OTLP attribute value wrapper."""
    val = attr.get("value", {})
    for key in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if key in val:
            return val[key]
    # arrayValue, kvlistValue, bytesValue: fall back to string repr
    return str(val)


def _attrs_to_dict(attributes: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert OTLP repeated KeyValue attributes to a flat dict."""
    return {a["key"]: _attr_value(a) for a in (attributes or [])}


# ---------------------------------------------------------------------------
# Metric parser
# ---------------------------------------------------------------------------


def parse_otlp_metrics(data: dict[str, Any]) -> pd.DataFrame:
    """Parse OTLP metric JSON into a tabular DataFrame.

    Expects the OTLP ExportMetricsServiceRequest JSON structure::

        {
          "resourceMetrics": [{
            "resource": {"attributes": [...]},
            "scopeMetrics": [{
              "metrics": [{
                "name": "...",
                "gauge": {"dataPoints": [{...}]} | "sum": {"dataPoints": [{...}]}
              }]
            }]
          }]
        }

    Returns a DataFrame with columns:
        service, metric_name, timestamp, value

    Each row represents one data point from one metric.
    """
    rows: list[dict[str, Any]] = []

    for rm in data.get("resourceMetrics", []):
        res_attrs = _attrs_to_dict(rm.get("resource", {}).get("attributes", []))
        service = res_attrs.get("service.name", "unknown")

        for sm in rm.get("scopeMetrics", []):
            for metric in sm.get("metrics", []):
                metric_name = metric.get("name", "unknown")

                # Data points can be under gauge, sum, histogram, or summary
                data_points: list[dict[str, Any]] = []
                for kind in ("gauge", "sum", "histogram", "summary"):
                    container = metric.get(kind, {})
                    if isinstance(container, dict):
                        data_points.extend(container.get("dataPoints", []))

                for dp in data_points:
                    ts_ns = int(dp.get("timeUnixNano", dp.get("startTimeUnixNano", "0")))
                    # Value can be asDouble, asInt, or count (for histogram/summary)
                    value = dp.get("asDouble", dp.get("asInt", dp.get("count", 0.0)))

                    # Extract data point attributes (e.g. container, pod labels)
                    dp_attrs = _attrs_to_dict(dp.get("attributes", []))

                    row: dict[str, Any] = {
                        "service": service,
                        "metric_name": metric_name,
                        "timestamp_ns": ts_ns,
                        "value": float(value),
                    }
                    # Promote common label attributes to columns
                    for label in ("container", "pod", "namespace", "host.name"):
                        if label in dp_attrs:
                            row[label.replace(".", "_")] = dp_attrs[label]
                        elif label in res_attrs:
                            row[label.replace(".", "_")] = res_attrs[label]

                    rows.append(row)

    if not rows:
        return pd.DataFrame(columns=["service", "metric_name", "timestamp", "value"])

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp_ns"], unit="ns", utc=True)
    df = df.drop(columns=["timestamp_ns"])
    return df


# ---------------------------------------------------------------------------
# Trace parser
# ---------------------------------------------------------------------------


def parse_otlp_traces(data: dict[str, Any]) -> pd.DataFrame:
    """Parse OTLP trace JSON into a tabular DataFrame of spans.

    Expects the OTLP ExportTraceServiceRequest JSON structure::

        {
          "resourceSpans": [{
            "resource": {"attributes": [...]},
            "scopeSpans": [{
              "spans": [{
                "traceId": "...", "spanId": "...", "name": "...",
                "startTimeUnixNano": "...", "endTimeUnixNano": "...",
                "status": {"code": 0}, "attributes": [...]
              }]
            }]
          }]
        }

    Returns a DataFrame with columns:
        trace_id, span_id, parent_span_id, service, operation,
        start_time, duration_us, status_code, kind
    """
    rows: list[dict[str, Any]] = []

    for rs in data.get("resourceSpans", []):
        res_attrs = _attrs_to_dict(rs.get("resource", {}).get("attributes", []))
        service = res_attrs.get("service.name", "unknown")

        for ss in rs.get("scopeSpans", []):
            for span in ss.get("spans", []):
                start_ns = int(span.get("startTimeUnixNano", "0"))
                end_ns = int(span.get("endTimeUnixNano", "0"))
                span_attrs = _attrs_to_dict(span.get("attributes", []))

                # HTTP status code from various OTel conventions
                status_code = span_attrs.get(
                    "http.status_code",
                    span_attrs.get(
                        "http.response.status_code",
                        str(span.get("status", {}).get("code", "")),
                    ),
                )

                rows.append(
                    {
                        "trace_id": span.get("traceId", ""),
                        "span_id": span.get("spanId", ""),
                        "parent_span_id": span.get("parentSpanId", ""),
                        "service": service,
                        "operation": span.get("name", ""),
                        "start_time_us": start_ns // 1000,
                        "duration_us": (end_ns - start_ns) // 1000,
                        "status_code": str(status_code),
                        "kind": span.get("kind", 0),
                    }
                )

    if not rows:
        return pd.DataFrame(
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

    df = pd.DataFrame(rows)
    df["start_time"] = pd.to_datetime(df["start_time_us"], unit="us", utc=True)
    df = df.drop(columns=["start_time_us"])
    df = df.drop_duplicates(subset=["trace_id", "span_id"])
    return df


# ---------------------------------------------------------------------------
# Log parser
# ---------------------------------------------------------------------------


def parse_otlp_logs(data: dict[str, Any]) -> pd.DataFrame:
    """Parse OTLP log JSON into a tabular DataFrame.

    Expects the OTLP ExportLogsServiceRequest JSON structure::

        {
          "resourceLogs": [{
            "resource": {"attributes": [...]},
            "scopeLogs": [{
              "logRecords": [{
                "timeUnixNano": "...",
                "severityText": "INFO",
                "body": {"stringValue": "..."},
                "attributes": [...]
              }]
            }]
          }]
        }

    Returns a DataFrame with columns:
        service, timestamp, severity, body
    """
    rows: list[dict[str, Any]] = []

    for rl in data.get("resourceLogs", []):
        res_attrs = _attrs_to_dict(rl.get("resource", {}).get("attributes", []))
        service = res_attrs.get("service.name", "unknown")

        for sl in rl.get("scopeLogs", []):
            for record in sl.get("logRecords", []):
                ts_ns = int(record.get("timeUnixNano", record.get("observedTimeUnixNano", "0")))
                severity = record.get("severityText", "UNSPECIFIED")
                body_val = record.get("body", {})
                if isinstance(body_val, dict):
                    body = body_val.get("stringValue", str(body_val))
                else:
                    body = str(body_val)

                rows.append(
                    {
                        "service": service,
                        "timestamp_ns": ts_ns,
                        "severity": severity,
                        "body": body,
                    }
                )

    if not rows:
        return pd.DataFrame(columns=["service", "timestamp", "severity", "body"])

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp_ns"], unit="ns", utc=True)
    df = df.drop(columns=["timestamp_ns"])
    return df
