"""Tests for alert dispatching (Slack and webhook)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from autosre.alerting.dispatcher import AlertDispatcher, AnomalyAlert
from autosre.config.schema import AlertingConfig, SlackConfig, WebhookConfig


@pytest.fixture
def sample_alert() -> AnomalyAlert:
    return AnomalyAlert(
        signal="metrics",
        model="isolation_forest",
        score=0.87,
        threshold=0.65,
        timestamp=datetime(2026, 4, 3, 12, 0, 0, tzinfo=timezone.utc),
        service="payment-api",
        details={"feature": "cpu_mean", "window": "5m"},
    )


@pytest.fixture
def critical_alert() -> AnomalyAlert:
    return AnomalyAlert(
        signal="traces",
        model="transformer_ae",
        score=0.98,
        threshold=0.40,
        timestamp=datetime(2026, 4, 3, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestAnomalyAlert:
    def test_to_dict(self, sample_alert):
        d = sample_alert.to_dict()
        assert d["signal"] == "metrics"
        assert d["model"] == "isolation_forest"
        assert d["score"] == 0.87
        assert d["threshold"] == 0.65
        assert d["service"] == "payment-api"
        assert d["details"]["feature"] == "cpu_mean"
        assert "2026-04-03" in d["timestamp"]

    def test_severity_warning(self, sample_alert):
        # score/threshold = 0.87/0.65 ~= 1.34 -> "info" (< 1.5)
        assert sample_alert.severity == "info"

    def test_severity_critical(self, critical_alert):
        # score/threshold = 0.98/0.40 = 2.45 -> "critical"
        assert critical_alert.severity == "critical"

    def test_severity_warning_level(self):
        alert = AnomalyAlert(
            signal="logs",
            model="ocsvm",
            score=0.75,
            threshold=0.50,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        # 0.75 / 0.50 = 1.5 -> "warning"
        assert alert.severity == "warning"

    def test_default_details(self):
        alert = AnomalyAlert(
            signal="metrics",
            model="if",
            score=0.5,
            threshold=0.5,
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert alert.to_dict()["details"] == {}

    def test_none_service(self):
        alert = AnomalyAlert(
            signal="metrics",
            model="if",
            score=0.5,
            threshold=0.5,
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert alert.to_dict()["service"] is None


class TestAlertDispatcher:
    def test_no_channels_configured(self, sample_alert):
        """Dispatcher with empty URLs should not make any HTTP calls."""
        config = AlertingConfig(
            slack=SlackConfig(webhook_url="", channel=""),
            webhook=WebhookConfig(url=""),
        )
        dispatcher = AlertDispatcher(config)
        # Should not raise.
        dispatcher.send(sample_alert)

    @patch("autosre.alerting.dispatcher.httpx.Client")
    def test_slack_called_when_configured(self, mock_client_cls, sample_alert):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        config = AlertingConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test", channel="#alerts"),
            webhook=WebhookConfig(url=""),
        )
        dispatcher = AlertDispatcher(config)
        dispatcher.send(sample_alert)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/test"
        payload = call_args[1]["json"]
        assert "blocks" in payload
        assert "Anomaly Detected" in payload["text"]

    @patch("autosre.alerting.dispatcher.httpx.Client")
    def test_webhook_called_when_configured(self, mock_client_cls, sample_alert):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        config = AlertingConfig(
            slack=SlackConfig(webhook_url=""),
            webhook=WebhookConfig(url="https://example.com/webhook"),
        )
        dispatcher = AlertDispatcher(config)
        dispatcher.send(sample_alert)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://example.com/webhook"
        payload = call_args[1]["json"]
        assert payload["event"] == "anomaly_detected"
        assert payload["alert"]["signal"] == "metrics"

    @patch("autosre.alerting.dispatcher.httpx.Client")
    def test_both_channels_called(self, mock_client_cls, sample_alert):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        config = AlertingConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test", channel="#alerts"),
            webhook=WebhookConfig(url="https://example.com/webhook"),
        )
        dispatcher = AlertDispatcher(config)
        dispatcher.send(sample_alert)

        assert mock_client.post.call_count == 2

    @patch("autosre.alerting.dispatcher.httpx.Client")
    def test_slack_block_contains_signal_and_model(self, mock_client_cls, sample_alert):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        config = AlertingConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test"),
            webhook=WebhookConfig(url=""),
        )
        dispatcher = AlertDispatcher(config)
        dispatcher.send(sample_alert)

        payload = mock_client.post.call_args[1]["json"]
        blocks = payload["blocks"]
        section_block = blocks[1]
        field_texts = [f["text"] for f in section_block["fields"]]
        assert any("metrics" in t for t in field_texts)
        assert any("isolation_forest" in t for t in field_texts)
        assert any("0.8700" in t for t in field_texts)
        assert any("payment-api" in t for t in field_texts)

    @patch("autosre.alerting.dispatcher.httpx.Client")
    def test_slack_failure_does_not_raise(self, mock_client_cls, sample_alert):
        """HTTP errors should be logged, not propagated."""
        import httpx

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.HTTPError("connection refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        config = AlertingConfig(
            slack=SlackConfig(webhook_url="https://hooks.slack.com/test"),
            webhook=WebhookConfig(url=""),
        )
        dispatcher = AlertDispatcher(config)
        # Should not raise.
        dispatcher.send(sample_alert)
