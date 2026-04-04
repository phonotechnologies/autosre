"""Tests for ClickHouseClient without requiring a running ClickHouse instance.

All clickhouse_connect interactions are mocked via pytest-mock.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_ch_client():
    """Return a MagicMock that stands in for clickhouse_connect.driver.Client."""
    client = MagicMock()
    client.command.return_value = 1
    client.insert_df.return_value = None
    client.query_df.return_value = pd.DataFrame()
    return client


@pytest.fixture()
def ch(mock_ch_client):
    """Create a ClickHouseClient with the underlying driver mocked out."""
    with patch("autosre.storage.clickhouse.clickhouse_connect") as mock_cc:
        mock_cc.get_client.return_value = mock_ch_client
        from autosre.storage.clickhouse import ClickHouseClient

        instance = ClickHouseClient(host="testhost", port=9000, database="testdb")
    # Swap in mock so subsequent calls hit it directly
    instance._client = mock_ch_client
    return instance


# ---------------------------------------------------------------------------
# from_config
# ---------------------------------------------------------------------------


class TestFromConfig:
    def test_creates_client_with_config_values(self, mock_ch_client):
        """from_config should pass StorageConfig fields to the constructor."""
        from autosre.config.schema import StorageConfig

        cfg = StorageConfig(
            clickhouse_host="ch.example.com",
            clickhouse_port=8443,
            clickhouse_database="prod_autosre",
        )

        with patch("autosre.storage.clickhouse.clickhouse_connect") as mock_cc:
            mock_cc.get_client.return_value = mock_ch_client
            from autosre.storage.clickhouse import ClickHouseClient

            client = ClickHouseClient.from_config(cfg)

        mock_cc.get_client.assert_called_once_with(
            host="ch.example.com", port=8443, database="prod_autosre"
        )
        assert client._host == "ch.example.com"
        assert client._port == 8443
        assert client._database == "prod_autosre"


# ---------------------------------------------------------------------------
# insert_spans
# ---------------------------------------------------------------------------


class TestInsertSpans:
    def test_calls_insert_df_with_spans_table(self, ch, mock_ch_client):
        df = pd.DataFrame(
            {
                "trace_id": ["a" * 32],
                "span_id": ["b" * 16],
                "parent_span_id": [""],
                "service": ["frontend"],
                "operation": ["GET /api"],
                "kind": [1],
                "status_code": ["200"],
                "start_time": [datetime(2026, 1, 1)],
                "duration_us": [1500],
                "resource_attrs": [{}],
                "span_attrs": [{}],
            }
        )
        count = ch.insert_spans(df)

        assert count == 1
        mock_ch_client.insert_df.assert_called_once()
        call_args = mock_ch_client.insert_df.call_args
        assert call_args[0][0] == "spans"

    def test_fills_missing_optional_columns(self, ch, mock_ch_client):
        """Missing columns like resource_attrs should get default values."""
        df = pd.DataFrame(
            {
                "trace_id": ["a" * 32],
                "span_id": ["b" * 16],
                "service": ["svc"],
                "operation": ["op"],
                "start_time": [datetime(2026, 1, 1)],
                "duration_us": [100],
            }
        )
        ch.insert_spans(df)

        inserted_df = mock_ch_client.insert_df.call_args[0][1]
        assert "parent_span_id" in inserted_df.columns
        assert "resource_attrs" in inserted_df.columns
        assert "span_attrs" in inserted_df.columns


# ---------------------------------------------------------------------------
# insert_metrics
# ---------------------------------------------------------------------------


class TestInsertMetrics:
    def test_calls_insert_df_with_metrics_table(self, ch, mock_ch_client):
        df = pd.DataFrame(
            {
                "service": ["api"],
                "metric_name": ["cpu_usage"],
                "timestamp": [datetime(2026, 1, 1)],
                "value": [0.85],
                "resource_attrs": [{}],
                "point_attrs": [{}],
            }
        )
        count = ch.insert_metrics(df)

        assert count == 1
        call_args = mock_ch_client.insert_df.call_args
        assert call_args[0][0] == "metrics"


# ---------------------------------------------------------------------------
# insert_logs
# ---------------------------------------------------------------------------


class TestInsertLogs:
    def test_calls_insert_df_with_logs_table(self, ch, mock_ch_client):
        df = pd.DataFrame(
            {
                "service": ["api"],
                "severity": ["ERROR"],
                "timestamp": [datetime(2026, 1, 1)],
                "body": ["NullPointerException"],
                "resource_attrs": [{}],
                "log_attrs": [{}],
                "trace_id": [""],
                "span_id": [""],
            }
        )
        count = ch.insert_logs(df)

        assert count == 1
        call_args = mock_ch_client.insert_df.call_args
        assert call_args[0][0] == "logs"


# ---------------------------------------------------------------------------
# read_features
# ---------------------------------------------------------------------------


class TestReadFeatures:
    def test_constructs_sql_with_signal_filter(self, ch, mock_ch_client):
        ch.read_features(signal="traces")

        sql = mock_ch_client.query_df.call_args[0][0]
        assert "signal = 'traces'" in sql
        assert "window_seconds = 60" in sql
        assert "ORDER BY timestamp" in sql

    def test_adds_service_filter(self, ch, mock_ch_client):
        ch.read_features(signal="metrics", service="frontend")

        sql = mock_ch_client.query_df.call_args[0][0]
        assert "service = 'frontend'" in sql

    def test_adds_time_range_filters(self, ch, mock_ch_client):
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 2)
        ch.read_features(signal="logs", start=start, end=end)

        sql = mock_ch_client.query_df.call_args[0][0]
        assert "timestamp >= '2026-01-01T00:00:00'" in sql
        assert "timestamp < '2026-01-02T00:00:00'" in sql

    def test_custom_window_seconds(self, ch, mock_ch_client):
        ch.read_features(signal="traces", window_seconds=300)

        sql = mock_ch_client.query_df.call_args[0][0]
        assert "window_seconds = 300" in sql


# ---------------------------------------------------------------------------
# write_scores
# ---------------------------------------------------------------------------


class TestWriteScores:
    def test_inserts_scores_with_defaults(self, ch, mock_ch_client):
        df = pd.DataFrame(
            {
                "timestamp": [datetime(2026, 1, 1)],
                "service": ["api"],
                "signal": ["traces"],
                "model": ["lstm_ae"],
                "score": [0.92],
                "threshold": [0.5],
                "is_anomaly": [1],
            }
        )
        count = ch.write_scores(df)

        assert count == 1
        call_args = mock_ch_client.insert_df.call_args
        assert call_args[0][0] == "anomaly_scores"


# ---------------------------------------------------------------------------
# write_cooldown_window
# ---------------------------------------------------------------------------


class TestWriteCooldownWindow:
    def test_generates_uuid_and_inserts(self, ch, mock_ch_client):
        start = datetime(2026, 1, 1, 12, 0, 0)
        end = datetime(2026, 1, 1, 12, 10, 0)

        cooldown_id = ch.write_cooldown_window(
            service="api",
            signal="traces",
            start_time=start,
            end_time=end,
            incident_id="inc-123",
        )

        # Should return a valid UUID string
        assert len(cooldown_id) == 36
        assert cooldown_id.count("-") == 4

        # Should call command with INSERT
        sql = mock_ch_client.command.call_args[0][0]
        assert "INSERT INTO cooldown_windows" in sql
        assert "api" in sql
        assert "traces" in sql
        assert "inc-123" in sql

    def test_computes_duration_minutes(self, ch, mock_ch_client):
        start = datetime(2026, 1, 1, 12, 0, 0)
        end = datetime(2026, 1, 1, 12, 15, 0)

        ch.write_cooldown_window(
            service="svc",
            signal="metrics",
            start_time=start,
            end_time=end,
        )

        sql = mock_ch_client.command.call_args[0][0]
        # 15 minutes
        assert "15)" in sql or ", 15)" in sql


# ---------------------------------------------------------------------------
# read_cooldown_windows
# ---------------------------------------------------------------------------


class TestReadCooldownWindows:
    def test_constructs_query_with_service_and_signal(self, ch, mock_ch_client):
        mock_ch_client.query_df.return_value = pd.DataFrame()
        result = ch.read_cooldown_windows(service="api", signal="traces")

        sql = mock_ch_client.query_df.call_args[0][0]
        assert "service = 'api'" in sql
        assert "signal = 'traces'" in sql
        assert result == []

    def test_adds_start_filter(self, ch, mock_ch_client):
        start = datetime(2026, 1, 1)
        mock_ch_client.query_df.return_value = pd.DataFrame()
        ch.read_cooldown_windows(service="api", signal="traces", start=start)

        sql = mock_ch_client.query_df.call_args[0][0]
        assert "end_time > '2026-01-01T00:00:00'" in sql

    def test_returns_list_of_dicts(self, ch, mock_ch_client):
        mock_ch_client.query_df.return_value = pd.DataFrame(
            {
                "cooldown_id": ["cw-1"],
                "service": ["api"],
                "signal": ["traces"],
                "start_time": [datetime(2026, 1, 1)],
                "end_time": [datetime(2026, 1, 1, 0, 10)],
            }
        )
        result = ch.read_cooldown_windows(service="api", signal="traces")

        assert len(result) == 1
        assert result[0]["cooldown_id"] == "cw-1"


# ---------------------------------------------------------------------------
# create_incident / read_incidents
# ---------------------------------------------------------------------------


class TestIncidents:
    def test_create_incident_returns_id(self, ch, mock_ch_client):
        incident_id = ch.create_incident(
            {
                "service": "api",
                "severity": "critical",
                "signals": ["traces", "metrics"],
            }
        )

        assert len(incident_id) == 36  # UUID
        sql = mock_ch_client.command.call_args[0][0]
        assert "INSERT INTO incidents" in sql

    def test_create_with_provided_id(self, ch, mock_ch_client):
        incident_id = ch.create_incident(
            {
                "incident_id": "custom-id-123",
                "service": "api",
            }
        )
        assert incident_id == "custom-id-123"

    def test_read_incidents_with_status_filter(self, ch, mock_ch_client):
        ch.read_incidents(status="open", limit=10)

        sql = mock_ch_client.query_df.call_args[0][0]
        assert "status = 'open'" in sql
        assert "LIMIT 10" in sql

    def test_read_incidents_no_filter(self, ch, mock_ch_client):
        ch.read_incidents()

        sql = mock_ch_client.query_df.call_args[0][0]
        assert "WHERE status" not in sql
        assert "LIMIT 50" in sql


# ---------------------------------------------------------------------------
# model_registry
# ---------------------------------------------------------------------------


class TestModelRegistry:
    def test_register_model_returns_id(self, ch, mock_ch_client):
        model_id = ch.register_model(
            {
                "model_name": "lstm_ae",
                "signal": "traces",
                "version": 1,
                "auc_roc": 0.85,
            }
        )

        assert len(model_id) == 36
        sql = mock_ch_client.command.call_args[0][0]
        assert "INSERT INTO model_registry" in sql
        assert "lstm_ae" in sql

    def test_get_active_model_returns_dict(self, ch, mock_ch_client):
        mock_ch_client.query_df.return_value = pd.DataFrame(
            {
                "model_id": ["m-1"],
                "model_name": ["lstm_ae"],
                "signal": ["traces"],
                "version": [3],
                "is_active": [1],
            }
        )
        result = ch.get_active_model("lstm_ae", "traces")

        assert result is not None
        assert result["model_name"] == "lstm_ae"
        assert result["version"] == 3
        sql = mock_ch_client.query_df.call_args[0][0]
        assert "is_active = 1" in sql
        assert "ORDER BY version DESC" in sql

    def test_get_active_model_returns_none_when_empty(self, ch, mock_ch_client):
        mock_ch_client.query_df.return_value = pd.DataFrame()
        result = ch.get_active_model("nonexistent", "traces")
        assert result is None


# ---------------------------------------------------------------------------
# ping
# ---------------------------------------------------------------------------


class TestPing:
    def test_returns_true_on_success(self, ch, mock_ch_client):
        mock_ch_client.command.return_value = 1
        assert ch.ping() is True

    def test_returns_false_on_failure(self, ch, mock_ch_client):
        mock_ch_client.command.side_effect = Exception("Connection refused")
        assert ch.ping() is False


# ---------------------------------------------------------------------------
# update_incident
# ---------------------------------------------------------------------------


class TestUpdateIncident:
    def test_reads_then_reinserts(self, ch, mock_ch_client):
        mock_ch_client.query_df.return_value = pd.DataFrame(
            {
                "incident_id": ["inc-1"],
                "started_at": ["2026-01-01T00:00:00"],
                "ended_at": ["2099-01-01T00:00:00"],
                "service": ["api"],
                "signals": [["traces"]],
                "models": [["lstm_ae"]],
                "severity": ["info"],
                "max_score": [0.5],
                "anomaly_count": [1],
                "status": ["open"],
                "root_cause": [""],
                "resolution": [""],
                "user_feedback": [""],
                "created_at": ["2026-01-01T00:00:00"],
                "updated_at": ["2026-01-01T00:00:00"],
            }
        )

        ch.update_incident("inc-1", {"status": "resolved", "resolution": "Scaled pods"})

        # Should have queried for the current row
        query_sql = mock_ch_client.query_df.call_args[0][0]
        assert "inc-1" in query_sql

        # Should have inserted the updated row
        insert_sql = mock_ch_client.command.call_args[0][0]
        assert "INSERT INTO incidents" in insert_sql
        assert "resolved" in insert_sql

    def test_raises_on_missing_incident(self, ch, mock_ch_client):
        mock_ch_client.query_df.return_value = pd.DataFrame()

        with pytest.raises(ValueError, match="not found"):
            ch.update_incident("nonexistent", {"status": "resolved"})


# ---------------------------------------------------------------------------
# ImportError handling
# ---------------------------------------------------------------------------


class TestImportError:
    def test_raises_import_error_when_missing(self):
        with patch.dict("sys.modules", {"clickhouse_connect": None}):
            # Force reimport
            import autosre.storage.clickhouse as mod

            orig_cc = mod.clickhouse_connect
            mod.clickhouse_connect = None
            try:
                with pytest.raises(ImportError, match="clickhouse-connect"):
                    mod._require_clickhouse_connect()
            finally:
                mod.clickhouse_connect = orig_cc
