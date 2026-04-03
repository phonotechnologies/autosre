"""Alert dispatching for anomaly detection events.

Sends structured alerts to Slack (rich block format) and generic webhooks
when anomaly scores exceed configured thresholds.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from autosre.config.schema import AlertingConfig

logger = logging.getLogger(__name__)


@dataclass
class AnomalyAlert:
    """Structured anomaly alert payload."""

    signal: str
    model: str
    score: float
    threshold: float
    timestamp: datetime
    service: str | None = None
    details: dict | None = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dictionary."""
        return {
            "signal": self.signal,
            "model": self.model,
            "score": self.score,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "service": self.service,
            "details": self.details or {},
        }

    @property
    def severity(self) -> str:
        """Derive severity from how far score exceeds threshold."""
        ratio = self.score / max(self.threshold, 1e-8)
        if ratio >= 2.0:
            return "critical"
        if ratio >= 1.5:
            return "warning"
        return "info"


class AlertDispatcher:
    """Dispatch anomaly alerts to Slack and webhooks.

    Configured via AlertingConfig from the YAML config. Channels with empty
    URLs are silently skipped, so callers do not need to guard against
    misconfiguration.
    """

    def __init__(self, config: AlertingConfig, timeout: float = 10.0):
        self._config = config
        self._timeout = timeout

    def send(self, alert: AnomalyAlert) -> None:
        """Send alert to all configured channels.

        Failures on individual channels are logged but do not prevent
        delivery to other channels.
        """
        if self._config.slack.webhook_url:
            self._send_slack(alert)
        if self._config.webhook.url:
            self._send_webhook(alert)

    def _send_slack(self, alert: AnomalyAlert) -> None:
        """Send via Slack incoming webhook (POST to webhook_url).

        Uses Slack Block Kit for rich formatting with signal, model, score,
        threshold, severity, and timestamp.
        """
        severity = alert.severity
        emoji = {"critical": ":red_circle:", "warning": ":warning:", "info": ":large_blue_circle:"}
        color = {"critical": "#E01E5A", "warning": "#ECB22E", "info": "#36C5F0"}

        service_text = f" on *{alert.service}*" if alert.service else ""
        header = f"{emoji.get(severity, ':bell:')} Anomaly Detected{service_text}"

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Anomaly Detected ({severity.upper()})"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Signal:*\n{alert.signal}"},
                    {"type": "mrkdwn", "text": f"*Model:*\n{alert.model}"},
                    {"type": "mrkdwn", "text": f"*Score:*\n{alert.score:.4f}"},
                    {"type": "mrkdwn", "text": f"*Threshold:*\n{alert.threshold:.4f}"},
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Timestamp: {alert.timestamp.isoformat()}",
                    },
                ],
            },
        ]

        if alert.service:
            blocks[1]["fields"].append({"type": "mrkdwn", "text": f"*Service:*\n{alert.service}"})

        payload = {
            "text": header,
            "blocks": blocks,
            "attachments": [{"color": color.get(severity, "#808080")}],
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(self._config.slack.webhook_url, json=payload)
                resp.raise_for_status()
            logger.info(
                "Slack alert sent for %s/%s (score=%.4f)", alert.signal, alert.model, alert.score
            )
        except httpx.HTTPError as exc:
            logger.error("Failed to send Slack alert: %s", exc)

    def _send_webhook(self, alert: AnomalyAlert) -> None:
        """Send via generic webhook (POST JSON payload).

        Posts the full alert dictionary to the configured URL. The receiving
        service is expected to accept JSON with Content-Type application/json.
        """
        payload = {
            "event": "anomaly_detected",
            "severity": alert.severity,
            "alert": alert.to_dict(),
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    self._config.webhook.url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
            logger.info(
                "Webhook alert sent for %s/%s (score=%.4f)", alert.signal, alert.model, alert.score
            )
        except httpx.HTTPError as exc:
            logger.error("Failed to send webhook alert: %s", exc)
