import logging
import os

from ..interface.job_opportunity import JobOpportunity
from ..interface.provider_result import ProviderSearchResult
from .base_provider import JobProvider, _env_float, _env_int

logger = logging.getLogger(__name__)


class AdzunaProvider(JobProvider):
    name = "adzuna"
    base_url = "https://api.adzuna.com/v1/api/jobs"
    country = "gb"
    results_per_page = _env_int("ADZUNA_RESULTS_PER_PAGE", 20)
    config_required = ("ADZUNA_APP_ID", "ADZUNA_API_KEY")
    min_interval_seconds = _env_float("ADZUNA_MIN_INTERVAL", 0.5)

    def __init__(
        self,
        *,
        results_per_page: int | None = None,
        min_interval_seconds: float | None = None,
        timeout: float | None = None,
        retries: int | None = None,
        backoff: float | None = None,
    ) -> None:
        super().__init__(
            timeout=timeout,
            retries=retries,
            backoff=backoff,
            min_interval_seconds=min_interval_seconds,
        )
        self.app_id = os.getenv("ADZUNA_APP_ID")
        self.api_key = os.getenv("ADZUNA_API_KEY")
        self.results_per_page = (
            results_per_page
            if results_per_page is not None
            else type(self).results_per_page
        )

    def search_jobs(
        self, role: str, location: str | None = None, **kwargs
    ) -> ProviderSearchResult:
        country = kwargs.get("country") or self.country
        page = kwargs.get("page", 1)
        url = f"{self.base_url}/{country}/search/{page}"

        params: dict = {
            "app_id": self.app_id,
            "app_key": self.api_key,
            "what": role,
            "results_per_page": kwargs.get("results_per_page", self.results_per_page),
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        for key in (
            "what_exclude",
            "what_phrase",
            "sort_by",
            "salary_min",
            "salary_max",
            "full_time",
            "permanent",
            "part_time",
            "contract",
            "distance",
            "category",
            "company",
            "max_days_old",
        ):
            if key in kwargs:
                params[key] = kwargs[key]

        logger.info(
            "job search role=%r location=%s provider=adzuna results_per_page=%d",
            role,
            location,
            params["results_per_page"],
        )
        data = self._get_json(
            url, params=params, headers={"Accept": "application/json"}
        )
        jobs, discarded = self._map_items(data.get("results", []))
        logger.debug(
            "adzuna mapped jobs=%d discarded=%d", len(jobs), len(discarded)
        )
        return ProviderSearchResult(
            provider=self.name, jobs=jobs, discarded_jobs=discarded
        )

    def _map_job(self, item: dict) -> JobOpportunity:
        company = item.get("company") or {}
        item_location = item.get("location") or {}
        return JobOpportunity(
            title=item.get("title", ""),
            description=item.get("description", ""),
            requirements=[],
            location=item_location.get("display_name", ""),
            company=company.get("display_name", ""),
            salary_range=self._build_salary_range(
                item.get("salary_min"), item.get("salary_max"), item.get("currency")
            ),
            employment_type=item.get("contract_time") or item.get("contract_type"),
            posted_date=item.get("created"),
            company_url=None,
            apply_url=item.get("redirect_url"),
        )