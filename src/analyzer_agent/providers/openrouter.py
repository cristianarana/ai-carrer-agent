import logging
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from core.config import load_settings
from ..errors import AnalysisProviderError
from .base import LLMProvider

logger = logging.getLogger(__name__)

_TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class OpenRouterProvider(LLMProvider):
    base_url = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        *,
        timeout: float | None = None,
        retries: int | None = None,
        backoff: float | None = None,
    ) -> None:
        api_key = api_key or os.getenv("OPENROUTER_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_KEY is not set")
        settings = load_settings()
        self._api_key = api_key
        self._model = model or settings.llm_model
        self._max_tokens = (
            max_tokens if max_tokens is not None else settings.openrouter_max_tokens
        )
        self.timeout = (
            timeout if timeout is not None else settings.openrouter_timeout
        )
        self.retries = (
            retries if retries is not None else settings.openrouter_retries
        )
        self.backoff = (
            backoff if backoff is not None else settings.openrouter_backoff
        )

    def generate_json(self, prompt: str) -> str:
        logger.info(
            "LLM request model=%s max_tokens=%s input_chars=%d",
            self._model,
            self._max_tokens,
            len(prompt),
        )
        attempt = 0
        while True:
            try:
                response = self._post_json_with_timing(prompt)
                logger.debug(
                    "LLM response received (attempt %d), content_chars=%d",
                    attempt + 1,
                    len(response),
                )
                return response
            except AnalysisProviderError as exc:
                if not exc.transient or attempt >= self.retries:
                    logger.error(
                        "LLM request failed permanently: %s", exc
                    )
                    raise
                if exc.status_code == 429 and exc.retry_after is not None:
                    wait = exc.retry_after
                else:
                    wait = self.backoff * (2**attempt)
                logger.warning(
                    "OpenRouter transient error (status=%s), retrying in %.1fs "
                    "(%d/%d)",
                    exc.status_code,
                    wait,
                    attempt + 1,
                    self.retries,
                )
                time.sleep(wait)
                attempt += 1

    def _post_json_with_timing(self, prompt: str) -> str:
        started = time.monotonic()
        try:
            return self._post_json(prompt)
        finally:
            logger.debug(
                "OpenRouter round-trip took %.2fs",
                time.monotonic() - started,
            )

    def _post_json(self, prompt: str) -> str:
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": self._max_tokens,
                },
                timeout=self.timeout,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise AnalysisProviderError(
                f"OpenRouter request failed: {exc}", transient=True
            ) from exc
        except requests.RequestException as exc:
            raise AnalysisProviderError(
                f"OpenRouter request failed: {exc}", transient=False
            ) from exc

        if response.status_code == 200:
            return self._extract_content(response.json())

        transient = response.status_code in _TRANSIENT_STATUS_CODES
        raise AnalysisProviderError(
            self._error_message(response),
            status_code=response.status_code,
            transient=transient,
            retry_after=self._retry_after_seconds(response),
        )

    @staticmethod
    def _extract_content(payload: dict) -> str:
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AnalysisProviderError(
                f"OpenRouter response missing 'choices[0].message.content': {payload}",
                transient=False,
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise AnalysisProviderError(
                f"OpenRouter returned empty content: {payload!r}", transient=False
            )
        return content

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            return (
                f"OpenRouter API error (HTTP {response.status_code}): "
                f"{response.text or response.reason}"
            )
        detail = body.get("error", {})
        return (
            f"OpenRouter API error (HTTP {response.status_code}): "
            f"{detail.get('message', body)}"
        )

    @staticmethod
    def _retry_after_seconds(response: requests.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            pass
        try:
            retry_at = parsedate_to_datetime(value)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None