"""LLM inference via OpenAI-compatible API (ollama for dev, vLLM for production)."""

from autosre.inference.client import LLMClient

__all__ = ["LLMClient"]
