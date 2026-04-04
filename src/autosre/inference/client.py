"""OpenAI-compatible LLM client for ollama (dev) and vLLM (production).

Both ollama and vLLM serve an OpenAI-compatible /v1/chat/completions endpoint.
This client wraps httpx to call that endpoint. No openai SDK dependency needed.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from autosre.config.schema import LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Parsed LLM response."""

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str


class LLMClient:
    """OpenAI-compatible LLM client.

    Works with any provider that serves /v1/chat/completions:
    - ollama (local dev): endpoint = http://localhost:11434/v1
    - vLLM (production): endpoint = http://localhost:8000/v1
    - OpenAI/Anthropic (fallback): standard endpoints
    """

    def __init__(self, config: LLMConfig | None = None):
        if config is None:
            config = LLMConfig()
        self.endpoint = config.endpoint.rstrip("/")
        self.model = config.model
        self.provider = config.provider
        self._client = httpx.Client(timeout=120.0)

    @classmethod
    def from_config(cls, config: LLMConfig) -> LLMClient:
        return cls(config)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Send a chat completion request."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        url = f"{self.endpoint}/chat/completions"
        try:
            resp = self._client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("LLM request failed: %s %s", e.response.status_code, e.response.text)
            raise
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to LLM at {url}. "
                f"Is {self.provider} running? "
                f"For local dev: ollama serve && ollama pull {self.model}"
            )

        data = resp.json()
        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    def analyze_anomaly(self, anomaly_context: dict) -> str:
        """Ask the LLM to analyze an anomaly and suggest root cause."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert SRE analyzing anomalies in a production system. "
                    "Given telemetry data about a detected anomaly, provide a concise "
                    "root cause analysis and recommended actions. Be specific and actionable."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Anomaly detected:\n"
                    f"- Service: {anomaly_context.get('service', 'unknown')}\n"
                    f"- Signal: {anomaly_context.get('signal', 'unknown')}\n"
                    f"- Model: {anomaly_context.get('model', 'unknown')}\n"
                    f"- Score: {anomaly_context.get('score', 0):.3f} "
                    f"(threshold: {anomaly_context.get('threshold', 0):.3f})\n"
                    f"- Timestamp: {anomaly_context.get('timestamp', 'unknown')}\n"
                    f"- Top features: {anomaly_context.get('top_features', 'N/A')}\n\n"
                    "What is the likely root cause? What should the on-call engineer check first?"
                ),
            },
        ]
        response = self.chat(messages, temperature=0.3, max_tokens=1024)
        return response.content

    def summarize_incident(self, incident_data: dict) -> str:
        """Generate a natural language summary of an incident."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an SRE writing an incident summary. Be concise, factual, "
                    "and focus on impact, timeline, and resolution."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Incident data:\n{json.dumps(incident_data, indent=2, default=str)}\n\n"
                    "Write a brief incident summary (3-5 sentences)."
                ),
            },
        ]
        response = self.chat(messages, temperature=0.2, max_tokens=512)
        return response.content

    def suggest_runbook(self, anomaly_context: dict) -> str:
        """Suggest a remediation runbook based on anomaly type."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an SRE creating a step-by-step remediation runbook. "
                    "Provide numbered steps that an on-call engineer can follow. "
                    "Include specific kubectl, curl, or CLI commands where relevant."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Anomaly:\n{json.dumps(anomaly_context, indent=2, default=str)}\n\n"
                    "Provide a remediation runbook (5-10 steps)."
                ),
            },
        ]
        response = self.chat(messages, temperature=0.2, max_tokens=1500)
        return response.content

    def ping(self) -> bool:
        """Check if the LLM endpoint is reachable."""
        try:
            resp = self._client.get(f"{self.endpoint}/models")
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def list_models(self) -> list[str]:
        """List available models from the endpoint."""
        try:
            resp = self._client.get(f"{self.endpoint}/models")
            resp.raise_for_status()
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except (httpx.ConnectError, httpx.HTTPStatusError, KeyError):
            return []

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> LLMClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
