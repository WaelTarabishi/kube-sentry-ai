"""Small HTTPX client for OpenRouter chat completions."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx
from loguru import logger


OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class LLMClientError(RuntimeError):
    """Safe application-level error for an unavailable or invalid LLM response."""


class OpenRouterClient:
    """Call OpenRouter with bounded retries and without logging secrets."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        http_client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.http_client = http_client
        self.sleep = sleep

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise LLMClientError("OPENROUTER_API_KEY is not configured")
        if not self.model:
            raise LLMClientError("OPENROUTER_MODEL is not configured")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = self._post(headers, payload)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < self.max_retries:
                    logger.warning(
                        "OpenRouter transport failure; retrying (attempt {}/{})",
                        attempt + 1,
                        self.max_retries + 1,
                    )
                    self.sleep(self._retry_delay(attempt))
                    continue
                logger.error("OpenRouter request failed after {} attempts", attempt + 1)
                raise LLMClientError("OpenRouter request failed") from exc

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                logger.warning(
                    "OpenRouter returned HTTP {}; retrying (attempt {}/{})",
                    response.status_code,
                    attempt + 1,
                    self.max_retries + 1,
                )
                self.sleep(self._retry_delay(attempt, response))
                continue

            if response.is_error:
                logger.error("OpenRouter returned HTTP {}", response.status_code)
                raise LLMClientError(
                    f"OpenRouter request failed with HTTP {response.status_code}"
                )

            return self._extract_content(response)

        raise LLMClientError("OpenRouter request failed")

    def _post(self, headers: dict[str, str], payload: dict[str, Any]) -> httpx.Response:
        if self.http_client is not None:
            return self.http_client.post(
                OPENROUTER_CHAT_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
        with httpx.Client(timeout=self.timeout_seconds) as client:
            return client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)

    @staticmethod
    def _extract_content(response: httpx.Response) -> str:
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise TypeError("response is not an object")
            if data.get("error"):
                raise KeyError("response contains an error")
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise KeyError("response content is empty")
            return content
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.error("OpenRouter returned an invalid completion payload")
            raise LLMClientError("OpenRouter returned an invalid response") from exc

    @staticmethod
    def _retry_delay(attempt: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            try:
                if retry_after is not None:
                    return min(max(float(retry_after), 0.0), 5.0)
            except ValueError:
                pass
        return 0.25 * (2**attempt)
