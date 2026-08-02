"""Unit tests for app.core.ai_reasoning.ollama_client.

The standard test suite never requires a live Ollama instance: every
response path (success, connection refused, timeout, non-success
status, malformed body) is exercised via an injected
`httpx.MockTransport`. One additional test is skipped automatically
unless Ollama is actually reachable on this machine, and only then
fires a real call against the configured local model.
"""

import json

import httpx
import pytest

from app.config.settings import settings
from app.core.ai_reasoning.exceptions import OllamaUnavailableError
from app.core.ai_reasoning.ollama_client import OllamaClient


def _client_with_handler(handler) -> OllamaClient:
    return OllamaClient(
        host="http://localhost:11434",
        model="llama3",
        timeout_seconds=5.0,
        transport=httpx.MockTransport(handler),
    )


def test_chat_json_returns_message_content_on_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        body = json.loads(request.content)
        assert body["model"] == "llama3"
        assert body["format"] == "json"
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"
        return httpx.Response(200, json={"message": {"role": "assistant", "content": '{"ok": true}'}})

    client = _client_with_handler(handler)
    content = client.chat_json("system prompt", "user prompt")

    assert content == '{"ok": true}'


def test_chat_json_raises_on_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_with_handler(handler)
    with pytest.raises(OllamaUnavailableError):
        client.chat_json("system", "user")


def test_chat_json_raises_on_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    client = _client_with_handler(handler)
    with pytest.raises(OllamaUnavailableError):
        client.chat_json("system", "user")


def test_chat_json_raises_on_non_success_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model not found"})

    client = _client_with_handler(handler)
    with pytest.raises(OllamaUnavailableError):
        client.chat_json("system", "user")


def test_chat_json_raises_on_unexpected_response_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    client = _client_with_handler(handler)
    with pytest.raises(OllamaUnavailableError):
        client.chat_json("system", "user")


def test_chat_json_raises_on_non_json_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    client = _client_with_handler(handler)
    with pytest.raises(OllamaUnavailableError):
        client.chat_json("system", "user")


def test_defaults_come_from_settings_when_not_overridden():
    client = OllamaClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    assert client._host == settings.OLLAMA_HOST.rstrip("/")
    assert client._model == settings.OLLAMA_MODEL


def _ollama_reachable() -> bool:
    try:
        response = httpx.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=2.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _ollama_reachable(), reason="Ollama is not reachable on this machine")
def test_chat_json_against_live_ollama():
    """Runs for real only when Ollama is actually reachable; skipped
    (not failed) otherwise."""
    client = OllamaClient()
    content = client.chat_json(
        "Respond with only the following JSON object, no other text: {\"ok\": true}",
        "ping",
    )
    assert content
    parsed = json.loads(content)
    assert isinstance(parsed, dict)
