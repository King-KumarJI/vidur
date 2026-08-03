"""
VIDUR Core - AI Reasoning
Submodule: Ollama Client
Purpose: Thin HTTP client for a local Ollama instance's chat API,
used to run genuine LLM-backed reasoning over Inspection Engine
findings, per the CLAUDE.md "Real AI/ML/DL/NLP Upgrade" amendment.
Ollama runs as a separate local service (like MongoDB/ChromaDB), never
a pip dependency and never a cloud endpoint - this client only ever
talks to the configured OLLAMA_HOST. Connection failures, timeouts,
and non-success responses are surfaced as OllamaUnavailableError so
callers can fall back to rule-based reasoning automatically, per
Article 10-11's non-crashing guarantee.
"""

from typing import Optional

import httpx

from app.config.logging_config import get_logger
from app.config.settings import settings
from app.core.ai_reasoning.exceptions import OllamaUnavailableError

logger = get_logger("ai_reasoning.ollama_client")


class OllamaClient:
    """Minimal client for Ollama's `/api/chat` endpoint, requesting a
    JSON-formatted response for downstream structured parsing."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        """`transport` is real (system default) unless injected, the
        same DI-for-tests pattern used elsewhere in this codebase
        (e.g. `local_agent.py`'s `psutil_module=psutil`) - it lets
        tests exercise every response path via `httpx.MockTransport`
        without a live Ollama instance."""
        self._host = (host or settings.OLLAMA_HOST).rstrip("/")
        self._model = model or settings.OLLAMA_MODEL
        self._timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.OLLAMA_TIMEOUT_SECONDS
        )
        self._transport = transport

    def chat_json(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat request to Ollama and return the raw text
        content of the model's response.

        Raises OllamaUnavailableError if Ollama cannot be reached,
        times out, responds with a non-success HTTP status, or
        responds with a body that does not match Ollama's own
        documented `/api/chat` response shape.
        """
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
        }
        url = f"{self._host}/api/chat"

        try:
            with httpx.Client(transport=self._transport, timeout=self._timeout_seconds) as client:
                response = client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(
                f"Ollama at '{self._host}' is unreachable or returned an error: {exc}"
            ) from exc

        try:
            body = response.json()
            return body["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise OllamaUnavailableError(
                f"Ollama at '{self._host}' returned an unexpected response shape: {exc}"
            ) from exc
