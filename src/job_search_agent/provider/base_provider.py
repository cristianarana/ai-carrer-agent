import time

import requests
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from pydantic import ValidationError

from ..interface.discarded_job import DiscardedJob
from ..interface.job_opportunity import JobOpportunity

load_dotenv()


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
    timeout = 15
    retries = 3
    backoff = 1.0
    discarded_jobs: list[DiscardedJob] = []

    @abstractmethod
    def search_jobs(
        self, role: str, location: str | None = None, **kwargs
    ) -> list[JobOpportunity]:
        raise NotImplementedError

    def _map_items(self, items: list[dict]) -> list[JobOpportunity]:
        self.discarded_jobs = []
        jobs: list[JobOpportunity] = []
        for item in items:
            try:
                jobs.append(self._map_job(item))
            except ValidationError as exc:
                self.discarded_jobs.append(
                    DiscardedJob(
                        provider=self.name,
                        source_title=item.get("title")
                        or item.get("job_title")
                        or "unknown",
                        reasons=[err.get("msg", str(err)) for err in exc.errors()],
                        raw=item,
                    )
                )
        return jobs

    def _get_json(
        self, url: str, params: dict | None = None, headers: dict | None = None
    ) -> dict:
        for attempt in range(self.retries + 1):
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
                    print(f"{self.name} API error ({status}): {cause}")
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
                print(
                    f"{self.name} transient error, retry in {wait:.1f}s "
                    f"({attempt + 1}/{self.retries})"
                )
                time.sleep(wait)
                continue
            print(f"{self.name} API error: {cause}")
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