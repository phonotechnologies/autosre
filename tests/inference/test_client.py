"""Tests for LLM inference client."""

from unittest.mock import MagicMock, patch

import pytest

from autosre.config.schema import LLMConfig
from autosre.inference.client import LLMClient, LLMResponse


@pytest.fixture
def config() -> LLMConfig:
    return LLMConfig(
        provider="ollama",
        endpoint="http://localhost:11434/v1",
        model="qwen2.5-coder:7b",
    )


@pytest.fixture
def client(config: LLMConfig) -> LLMClient:
    return LLMClient(config)


class TestLLMClient:
    def test_from_config(self, config):
        client = LLMClient.from_config(config)
        assert client.endpoint == "http://localhost:11434/v1"
        assert client.model == "qwen2.5-coder:7b"
        assert client.provider == "ollama"

    def test_default_config(self):
        client = LLMClient()
        assert client.provider == "ollama"
        assert "11434" in client.endpoint

    def test_endpoint_trailing_slash_stripped(self):
        cfg = LLMConfig(endpoint="http://localhost:8000/v1/")
        client = LLMClient(cfg)
        assert client.endpoint == "http://localhost:8000/v1"


class TestChat:
    def test_successful_chat(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {"content": "The service is overloaded."},
                    "finish_reason": "stop",
                }
            ],
            "model": "qwen2.5-coder:7b",
            "usage": {"prompt_tokens": 50, "completion_tokens": 10},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp):
            response = client.chat([{"role": "user", "content": "What is wrong?"}])

        assert isinstance(response, LLMResponse)
        assert response.content == "The service is overloaded."
        assert response.model == "qwen2.5-coder:7b"
        assert response.finish_reason == "stop"

    def test_json_mode(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": '{"root_cause": "OOM"}'}, "finish_reason": "stop"}],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp) as mock_post:
            client.chat([{"role": "user", "content": "Analyze"}], json_mode=True)
            payload = mock_post.call_args[1]["json"]
            assert payload["response_format"] == {"type": "json_object"}


class TestAnalyzeAnomaly:
    def test_returns_analysis_string(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": "CPU spike due to query storm."}, "finish_reason": "stop"}
            ],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp):
            result = client.analyze_anomaly(
                {
                    "service": "checkout",
                    "signal": "metrics",
                    "score": 0.95,
                    "threshold": 0.5,
                }
            )
        assert "CPU spike" in result


class TestSummarizeIncident:
    def test_returns_summary(self, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": "Incident summary here."}, "finish_reason": "stop"}
            ],
            "usage": {},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", return_value=mock_resp):
            result = client.summarize_incident({"service": "api", "status": "resolved"})
        assert "summary" in result.lower()


class TestPing:
    def test_ping_success(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(client._client, "get", return_value=mock_resp):
            assert client.ping() is True

    def test_ping_failure(self, client):
        import httpx

        with patch.object(client._client, "get", side_effect=httpx.ConnectError("refused")):
            assert client.ping() is False


class TestListModels:
    def test_returns_model_ids(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"id": "qwen2.5-coder:7b"},
                {"id": "deepseek-v3:latest"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(client._client, "get", return_value=mock_resp):
            models = client.list_models()
        assert models == ["qwen2.5-coder:7b", "deepseek-v3:latest"]

    def test_returns_empty_on_error(self, client):
        import httpx

        with patch.object(client._client, "get", side_effect=httpx.ConnectError("refused")):
            assert client.list_models() == []


class TestContextManager:
    def test_context_manager(self, config):
        with LLMClient(config) as client:
            assert client.provider == "ollama"


class TestLLMConfigDefaults:
    def test_ollama_default(self):
        cfg = LLMConfig.ollama_default()
        assert cfg.provider == "ollama"
        assert "11434" in cfg.endpoint

    def test_vllm_default(self):
        cfg = LLMConfig.vllm_default()
        assert cfg.provider == "vllm"
        assert "8000" in cfg.endpoint
        assert "Qwen" in cfg.model
