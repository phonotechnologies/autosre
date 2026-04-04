"""ClickHouse storage client for AutoSRE telemetry and detection data.

Wraps clickhouse-connect to provide typed methods for inserting raw
telemetry (spans, metrics, logs), reading features, writing anomaly
scores, managing incidents, cooldown windows, and model registry entries.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from autosre.config.schema import StorageConfig

try:
    import clickhouse_connect
    from clickhouse_connect.driver.client import Client as CHClient
except ImportError:
    clickhouse_connect = None  # type: ignore[assignment]
    CHClient = None  # type: ignore[assignment, misc]


def _require_clickhouse_connect() -> None:
    if clickhouse_connect is None:
        raise ImportError(
            "clickhouse-connect is required for ClickHouseClient. "
            "Install it with: pip install clickhouse-connect"
        )


# Column definitions for raw telemetry tables.
# Order must match the ClickHouse table schema for insert_df.
SPANS_COLUMNS = [
    "trace_id",
    "span_id",
    "parent_span_id",
    "service",
    "operation",
    "kind",
    "status_code",
    "start_time",
    "duration_us",
    "resource_attrs",
    "span_attrs",
]

METRICS_COLUMNS = [
    "service",
    "metric_name",
    "timestamp",
    "value",
    "resource_attrs",
    "point_attrs",
]

LOGS_COLUMNS = [
    "service",
    "severity",
    "timestamp",
    "body",
    "resource_attrs",
    "log_attrs",
    "trace_id",
    "span_id",
]


class ClickHouseClient:
    """High-level ClickHouse client for AutoSRE data operations.

    All methods raise ``clickhouse_connect`` exceptions on connection or
    query failures. Callers should handle these at the CLI / API layer.
    """

    def __init__(self, host: str, port: int, database: str) -> None:
        _require_clickhouse_connect()
        self._host = host
        self._port = port
        self._database = database
        self._client: CHClient = clickhouse_connect.get_client(
            host=host, port=port, database=database
        )

    @classmethod
    def from_config(cls, config: StorageConfig) -> ClickHouseClient:
        """Create a ClickHouseClient from an AutoSRE StorageConfig."""
        return cls(
            host=config.clickhouse_host,
            port=config.clickhouse_port,
            database=config.clickhouse_database,
        )

    # ------------------------------------------------------------------
    # Raw data writes
    # ------------------------------------------------------------------

    def insert_spans(self, df: pd.DataFrame) -> int:
        """Insert a DataFrame of trace spans into the spans table.

        Expected columns match ``SPANS_COLUMNS``. Missing optional columns
        (parent_span_id, resource_attrs, span_attrs) are filled with defaults.

        Returns:
            Number of rows inserted.
        """
        df = _prepare_df(
            df,
            SPANS_COLUMNS,
            defaults={
                "parent_span_id": "",
                "kind": 0,
                "status_code": "",
                "resource_attrs": dict,
                "span_attrs": dict,
            },
        )
        self._client.insert_df("spans", df, column_names=list(df.columns))
        return len(df)

    def insert_metrics(self, df: pd.DataFrame) -> int:
        """Insert a DataFrame of metric data points.

        Returns:
            Number of rows inserted.
        """
        df = _prepare_df(
            df,
            METRICS_COLUMNS,
            defaults={
                "resource_attrs": dict,
                "point_attrs": dict,
            },
        )
        self._client.insert_df("metrics", df, column_names=list(df.columns))
        return len(df)

    def insert_logs(self, df: pd.DataFrame) -> int:
        """Insert a DataFrame of log records.

        Returns:
            Number of rows inserted.
        """
        df = _prepare_df(
            df,
            LOGS_COLUMNS,
            defaults={
                "severity": "UNSPECIFIED",
                "resource_attrs": dict,
                "log_attrs": dict,
                "trace_id": "",
                "span_id": "",
            },
        )
        self._client.insert_df("logs", df, column_names=list(df.columns))
        return len(df)

    # ------------------------------------------------------------------
    # Feature reads
    # ------------------------------------------------------------------

    def read_features(
        self,
        signal: str,
        service: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        window_seconds: int = 60,
    ) -> pd.DataFrame:
        """Read feature rows from the features table.

        Applies optional filters for service, time range, and window size.

        Returns:
            DataFrame with all feature columns for the matching rows.
        """
        conditions = [
            f"signal = '{_esc(signal)}'",
            f"window_seconds = {window_seconds}",
        ]
        if service is not None:
            conditions.append(f"service = '{_esc(service)}'")
        if start is not None:
            conditions.append(f"timestamp >= '{start.isoformat()}'")
        if end is not None:
            conditions.append(f"timestamp < '{end.isoformat()}'")

        where = " AND ".join(conditions)
        sql = f"SELECT * FROM features WHERE {where} ORDER BY timestamp"
        return self._client.query_df(sql)

    # ------------------------------------------------------------------
    # Score writes
    # ------------------------------------------------------------------

    def write_scores(self, df: pd.DataFrame) -> int:
        """Insert anomaly detection scores into anomaly_scores table.

        Expected columns: timestamp, service, signal, model, score,
        threshold, is_anomaly. Optional: fusion_*, model_version,
        window_seconds, severity, details.

        Returns:
            Number of rows inserted.
        """
        defaults = {
            "fusion_max": 0.0,
            "fusion_avg": 0.0,
            "fusion_weighted": 0.0,
            "fusion_vote": 0,
            "model_version": "",
            "window_seconds": 60,
            "severity": "info",
            "details": "{}",
        }
        required = [
            "timestamp",
            "service",
            "signal",
            "model",
            "score",
            "threshold",
            "is_anomaly",
        ]
        cols = required + [c for c in defaults if c in df.columns or c not in required]
        df = _prepare_df(df, cols, defaults=defaults)
        self._client.insert_df("anomaly_scores", df, column_names=list(df.columns))
        return len(df)

    # ------------------------------------------------------------------
    # Incident management
    # ------------------------------------------------------------------

    def create_incident(self, incident: dict[str, Any]) -> str:
        """Create an incident record. Returns the generated incident_id."""
        incident_id = incident.get("incident_id", str(uuid.uuid4()))
        defaults: dict[str, Any] = {
            "incident_id": incident_id,
            "started_at": datetime.now(UTC).isoformat(),
            "ended_at": "2099-01-01T00:00:00",
            "service": "",
            "signals": [],
            "models": [],
            "severity": "info",
            "max_score": 0.0,
            "anomaly_count": 0,
            "status": "open",
            "root_cause": "",
            "resolution": "",
            "user_feedback": "",
        }
        row = {**defaults, **incident, "incident_id": incident_id}
        cols = list(defaults.keys())
        values = ", ".join(_sql_value(row[c]) for c in cols)
        col_list = ", ".join(cols)
        self._client.command(f"INSERT INTO incidents ({col_list}) VALUES ({values})")
        return incident_id

    def update_incident(self, incident_id: str, updates: dict[str, Any]) -> None:
        """Update an incident by inserting a new row (ReplacingMergeTree).

        Reads the current row, merges updates, and re-inserts so that
        ClickHouse's ReplacingMergeTree keeps the latest version.
        """
        current_df = self._client.query_df(
            f"SELECT * FROM incidents FINAL WHERE incident_id = '{_esc(incident_id)}' LIMIT 1"
        )
        if current_df.empty:
            raise ValueError(f"Incident {incident_id} not found")

        row = current_df.iloc[0].to_dict()
        row.update(updates)
        row["updated_at"] = datetime.now(UTC).isoformat()

        # Re-insert columns that match the table schema
        insert_cols = [
            "incident_id",
            "started_at",
            "ended_at",
            "service",
            "signals",
            "models",
            "severity",
            "max_score",
            "anomaly_count",
            "status",
            "root_cause",
            "resolution",
            "user_feedback",
            "created_at",
            "updated_at",
        ]
        available = [c for c in insert_cols if c in row]
        values = ", ".join(_sql_value(row[c]) for c in available)
        col_list = ", ".join(available)
        self._client.command(f"INSERT INTO incidents ({col_list}) VALUES ({values})")

    def read_incidents(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        """Read incidents, optionally filtered by status."""
        where = f"WHERE status = '{_esc(status)}'" if status else ""
        sql = f"SELECT * FROM incidents FINAL {where} ORDER BY started_at DESC LIMIT {limit}"
        return self._client.query_df(sql)

    # ------------------------------------------------------------------
    # Cooldown windows
    # ------------------------------------------------------------------

    def write_cooldown_window(
        self,
        service: str,
        signal: str,
        start_time: datetime,
        end_time: datetime,
        incident_id: str = "",
    ) -> str:
        """Write a cooldown exclusion window. Returns the generated cooldown_id."""
        cooldown_id = str(uuid.uuid4())
        duration_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
        self._client.command(
            f"INSERT INTO cooldown_windows "
            f"(cooldown_id, service, signal, incident_id, "
            f"start_time, end_time, duration_minutes) VALUES ("
            f"'{_esc(cooldown_id)}', '{_esc(service)}', '{_esc(signal)}', "
            f"'{_esc(incident_id)}', "
            f"'{start_time.isoformat()}', '{end_time.isoformat()}', "
            f"{duration_minutes})"
        )
        return cooldown_id

    def read_cooldown_windows(
        self,
        service: str,
        signal: str,
        start: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Read cooldown windows for a service/signal pair.

        Returns:
            List of dicts with cooldown_id, service, signal, incident_id,
            start_time, end_time, duration_minutes, created_at.
        """
        conditions = [
            f"service = '{_esc(service)}'",
            f"signal = '{_esc(signal)}'",
        ]
        if start is not None:
            conditions.append(f"end_time > '{start.isoformat()}'")

        where = " AND ".join(conditions)
        sql = f"SELECT * FROM cooldown_windows WHERE {where} ORDER BY start_time"
        df = self._client.query_df(sql)
        return df.to_dict(orient="records") if not df.empty else []

    # ------------------------------------------------------------------
    # Model registry
    # ------------------------------------------------------------------

    def register_model(self, model_info: dict[str, Any]) -> str:
        """Register a trained model in the model_registry table.

        Returns:
            The generated model_id.
        """
        model_id = model_info.get("model_id", str(uuid.uuid4()))
        defaults: dict[str, Any] = {
            "model_id": model_id,
            "model_name": "",
            "signal": "",
            "version": 1,
            "is_active": 1,
            "trained_at": datetime.now(UTC).isoformat(),
            "training_samples": 0,
            "n_features": 0,
            "seq_length": 30,
            "window_seconds": 60,
            "hyperparameters": "{}",
            "threshold": 0.5,
            "threshold_method": "percentile",
            "auc_roc": 0.0,
            "f1_score": 0.0,
            "precision_score": 0.0,
            "recall_score": 0.0,
            "artifact_path": "",
            "feature_columns": [],
        }
        row = {**defaults, **model_info, "model_id": model_id}
        cols = list(defaults.keys())
        values = ", ".join(_sql_value(row[c]) for c in cols)
        col_list = ", ".join(cols)
        self._client.command(f"INSERT INTO model_registry ({col_list}) VALUES ({values})")
        return model_id

    def get_active_model(self, model_name: str, signal: str) -> dict[str, Any] | None:
        """Get the latest active model for a given name and signal.

        Returns:
            Dict of model metadata, or None if no active model exists.
        """
        sql = (
            f"SELECT * FROM model_registry FINAL "
            f"WHERE model_name = '{_esc(model_name)}' "
            f"AND signal = '{_esc(signal)}' "
            f"AND is_active = 1 "
            f"ORDER BY version DESC LIMIT 1"
        )
        df = self._client.query_df(sql)
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Check ClickHouse connectivity. Returns True if the server responds."""
        try:
            self._client.command("SELECT 1")
            return True
        except Exception:
            return False


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _esc(value: str) -> str:
    """Escape single quotes for ClickHouse SQL strings."""
    return str(value).replace("'", "\\'")


def _sql_value(value: Any) -> str:
    """Convert a Python value to a ClickHouse SQL literal."""
    if value is None:
        return "''"
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        inner = ", ".join(f"'{_esc(str(v))}'" for v in value)
        return f"[{inner}]"
    if isinstance(value, dict):
        # Map literal
        keys = ", ".join(f"'{_esc(str(k))}'" for k in value.keys())
        vals = ", ".join(f"'{_esc(str(v))}'" for v in value.values())
        return f"map({keys}, {vals})" if value else "map()"
    return f"'{_esc(str(value))}'"


def _prepare_df(
    df: pd.DataFrame,
    columns: list[str],
    defaults: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Reorder and fill missing columns in a DataFrame for insert.

    Args:
        df: Input DataFrame.
        columns: Expected column order.
        defaults: Default values for missing columns. If the value is a
            callable (e.g. ``dict``), it is called per-row via apply.

    Returns:
        DataFrame with columns in the correct order.
    """
    defaults = defaults or {}
    result = df.copy()

    for col in columns:
        if col not in result.columns:
            default = defaults.get(col, "")
            if callable(default):
                result[col] = [default() for _ in range(len(result))]
            else:
                result[col] = default

    # Return only the requested columns in order
    return result[[c for c in columns if c in result.columns]]
