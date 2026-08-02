import json

import httpx
import pytest

from app.ai.llm_client import LLMClientError, OpenRouterClient


def test_openrouter_client_retries_transient_failure_and_returns_content() -> None:
    requests: list[httpx.Request] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(503, headers={"Retry-After": "1"}, request=request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"root_cause":"x"}'}}]},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenRouterClient(
        api_key="test-secret",
        model="test/model",
        http_client=http_client,
        sleep=delays.append,
    )

    assert client.complete([{"role": "user", "content": "evidence"}]) == (
        '{"root_cause":"x"}'
    )
    assert len(requests) == 2
    assert delays == [1.0]
    assert requests[0].headers["Authorization"] == "Bearer test-secret"
    body = json.loads(requests[0].content)
    assert body["model"] == "test/model"
    assert body["temperature"] == 0
    assert body["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("api_key,model", [("", "test/model"), ("secret", "")])
def test_openrouter_client_requires_configuration(api_key: str, model: str) -> None:
    client = OpenRouterClient(api_key=api_key, model=model)

    with pytest.raises(LLMClientError, match="is not configured"):
        client.complete([])


def test_openrouter_client_hides_error_response_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"message": "secret provider detail"}},
            request=request,
        )

    client = OpenRouterClient(
        api_key="test-secret",
        model="test/model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(LLMClientError, match="HTTP 401") as error:
        client.complete([])

    assert "secret provider detail" not in str(error.value)
    assert "test-secret" not in str(error.value)


def test_openrouter_client_retries_timeouts_then_fails_cleanly() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("provider timed out", request=request)

    client = OpenRouterClient(
        api_key="test-secret",
        model="test/model",
        max_retries=1,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
    )

    with pytest.raises(LLMClientError, match="request failed"):
        client.complete([])

    assert attempts == 2
