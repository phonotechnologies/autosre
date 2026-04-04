"""YAML configuration schema for AutoSRE."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TelemetryConfig:
    endpoint: str = "localhost:4317"
    protocol: str = "grpc"
    signals: list[str] = field(default_factory=lambda: ["metrics", "traces", "logs"])


@dataclass
class StorageConfig:
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "autosre"
    model_dir: str = "./models"


@dataclass
class CooldownDetectionConfig:
    enabled: bool = True
    default_duration_minutes: int = 10


@dataclass
class DetectionConfig:
    models: list[str] = field(default_factory=lambda: ["auto"])
    cooldown: CooldownDetectionConfig = field(default_factory=CooldownDetectionConfig)
    threshold_method: str = "percentile"
    optuna_trials: int = 300
    seq_length: int = 30
    window_minutes: int = 1


@dataclass
class LLMConfig:
    provider: str = "ollama"
    endpoint: str = "http://localhost:11434/v1"
    model: str = "qwen2.5-coder:7b"

    @staticmethod
    def ollama_default() -> LLMConfig:
        """Local dev defaults (ollama)."""
        return LLMConfig(
            provider="ollama",
            endpoint="http://localhost:11434/v1",
            model="qwen2.5-coder:7b",
        )

    @staticmethod
    def vllm_default() -> LLMConfig:
        """Production defaults (vLLM on GPU)."""
        return LLMConfig(
            provider="vllm",
            endpoint="http://localhost:8000/v1",
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
        )


@dataclass
class SlackConfig:
    webhook_url: str = ""
    channel: str = ""


@dataclass
class WebhookConfig:
    url: str = ""


@dataclass
class AlertingConfig:
    slack: SlackConfig = field(default_factory=SlackConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)


@dataclass
class AutoSREConfig:
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    alerting: AlertingConfig = field(default_factory=AlertingConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> AutoSREConfig:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> AutoSREConfig:
        config = cls()
        if "telemetry" in data:
            t = data["telemetry"]
            config.telemetry = TelemetryConfig(
                endpoint=t.get("endpoint", config.telemetry.endpoint),
                protocol=t.get("protocol", config.telemetry.protocol),
                signals=t.get("signals", config.telemetry.signals),
            )
        if "storage" in data:
            s = data["storage"]
            config.storage = StorageConfig(
                clickhouse_host=s.get("clickhouse_host", config.storage.clickhouse_host),
                clickhouse_port=s.get("clickhouse_port", config.storage.clickhouse_port),
                clickhouse_database=s.get(
                    "clickhouse_database", config.storage.clickhouse_database
                ),
                model_dir=s.get("model_dir", config.storage.model_dir),
            )
        if "detection" in data:
            d = data["detection"]
            cooldown_data = d.get("cooldown", {})
            config.detection = DetectionConfig(
                models=d.get("models", config.detection.models),
                cooldown=CooldownDetectionConfig(
                    enabled=cooldown_data.get("enabled", True),
                    default_duration_minutes=cooldown_data.get("default_duration_minutes", 10),
                ),
                threshold_method=d.get("threshold_method", config.detection.threshold_method),
                optuna_trials=d.get("optuna_trials", config.detection.optuna_trials),
                seq_length=d.get("seq_length", config.detection.seq_length),
                window_minutes=d.get("window_minutes", config.detection.window_minutes),
            )
        if "llm" in data:
            ll = data["llm"]
            config.llm = LLMConfig(
                provider=ll.get("provider", config.llm.provider),
                endpoint=ll.get("endpoint", config.llm.endpoint),
                model=ll.get("model", config.llm.model),
            )
        if "alerting" in data:
            a = data["alerting"]
            slack = a.get("slack", {})
            webhook = a.get("webhook", {})
            config.alerting = AlertingConfig(
                slack=SlackConfig(
                    webhook_url=slack.get("webhook_url", ""),
                    channel=slack.get("channel", ""),
                ),
                webhook=WebhookConfig(url=webhook.get("url", "")),
            )
        return config

    def to_yaml(self, path: str | Path) -> None:
        data = {
            "telemetry": {
                "endpoint": self.telemetry.endpoint,
                "protocol": self.telemetry.protocol,
                "signals": self.telemetry.signals,
            },
            "storage": {
                "clickhouse_host": self.storage.clickhouse_host,
                "clickhouse_port": self.storage.clickhouse_port,
                "clickhouse_database": self.storage.clickhouse_database,
                "model_dir": self.storage.model_dir,
            },
            "detection": {
                "models": self.detection.models,
                "cooldown": {
                    "enabled": self.detection.cooldown.enabled,
                    "default_duration_minutes": self.detection.cooldown.default_duration_minutes,
                },
                "threshold_method": self.detection.threshold_method,
                "optuna_trials": self.detection.optuna_trials,
                "seq_length": self.detection.seq_length,
                "window_minutes": self.detection.window_minutes,
            },
            "llm": {
                "provider": self.llm.provider,
                "endpoint": self.llm.endpoint,
                "model": self.llm.model,
            },
            "alerting": {
                "slack": {
                    "webhook_url": self.alerting.slack.webhook_url,
                    "channel": self.alerting.slack.channel,
                },
                "webhook": {"url": self.alerting.webhook.url},
            },
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
