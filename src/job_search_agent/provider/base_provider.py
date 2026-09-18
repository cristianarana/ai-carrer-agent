import logging
import os
import threading
import time

import requests
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from pydantic import ValidationError

from ..interface.discarded_job import DiscardedJob
from ..interface.job_opportunity import JobOpportunity
from ..interface.provider_result import ProviderSearchResult

logger = logging.getLogger(__name__)

load_dotenv()


class _RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self, min_interval: float) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_call
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_call = time.monotonic()


_RATE_LIMITERS: dict[str, _RateLimiter] = {}
_RATE_LIMITERS_GUARD = threading.Lock()


def _wait_for_rate_limit(name: str, min_interval: float) -> None:
    if min_interval <= 0.0:
        return
    with _RATE_LIMITERS_GUARD:
        limiter = _RATE_LIMITERS.get(name)
        if limiter is None:
            limiter = _RateLimiter()
            _RATE_LIMITERS[name] = limiter
    limiter.wait(min_interval)


class ProviderError(Exception):
    def __init__(
        self,
        provider: str,
        message: str,
        *,
        status_code: int | None = None,
        transient: bool = False,
    ):
        self.provider = provider
        self.status_code = status_code
        self.transient = transient
        super().__init__(f"{provider} error: {message}")


class JobProvider(ABC):
    name: str
    base_url: str
    config_required: tuple[str, ...] = ()
    timeout = 15
    retries = 3
    backoff = 1.0
    min_interval_seconds = 0.0
    search_mode = "per_position"

    def is_configured(self) -> bool:
        return all(os.getenv(key) for key in self.config_required)

    @abstractmethod
    def search_jobs(
        self, role: str, location: str | None = None, **kwargs
    ) -> ProviderSearchResult:
        raise NotImplementedError

    def _map_items(
        self, items: list[dict]
    ) -> tuple[list[JobOpportunity], list[DiscardedJob]]:
        jobs: list[JobOpportunity] = []
        discarded: list[DiscardedJob] = []
        for item in items:
            try:
                job = self._map_job(item)
                jobs.append(job.model_copy(update={"source_provider": self.name}))
            except ValidationError as exc:
                discarded.append(
                    DiscardedJob(
                        provider=self.name,
                        source_title=item.get("title")
                        or item.get("job_title")
                        or "unknown",
                        reasons=[err.get("msg", str(err)) for err in exc.errors()],
                        raw=item,
                    )
                )
        return jobs, discarded

    def _get_json(
        self, url: str, params: dict | None = None, headers: dict | None = None
    ) -> dict:
        for attempt in range(self.retries + 1):
            _wait_for_rate_limit(self.name, self.min_interval_seconds)
            try:
                response = requests.get(
                    url, params=params, headers=headers, timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except (requests.Timeout, requests.ConnectionError) as e:
                transient, status, cause = True, None, e
            except requests.HTTPError as e:
                status = e.response.status_code
                transient, cause = status >= 500, e
                if not transient:
                    logger.error("%s API error (%s): %s", self.name, status, cause)
                    raise ProviderError(
                        self.name,
                        str(cause),
                        status_code=status,
                        transient=False,
                    ) from cause
            except requests.RequestException as e:
                transient, status, cause = False, None, e

            if transient and attempt < self.retries:
                wait = self.backoff * (2**attempt)
                logger.warning(
                    "%s transient error, retry in %.1fs (%d/%d)",
                    self.name,
                    wait,
                    attempt + 1,
                    self.retries,
                )
                time.sleep(wait)
                continue
            logger.error("%s API error: %s", self.name, cause)
            raise ProviderError(self.name, str(cause), status_code=status) from cause

    @staticmethod
    def _build_salary_range(
        minimum: float | None,
        maximum: float | None,
        currency: str | None = None,
        period: str | None = None,
    ) -> str | None:
        if minimum is None and maximum is None:
            return None
        low = str(minimum) if minimum is not None else ""
        high = str(maximum) if maximum is not None else ""
        salary = (
            f"{low} - {high}"
            if minimum is not None and maximum is not None
            else (low or high)
        )
        suffix = " ".join(part for part in (currency, period) if part)
        return f"{salary} {suffix}".strip() if suffix else salary