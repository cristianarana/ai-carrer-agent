import os

from ..interface.job_opportunity import JobOpportunity
from .base_provider import JobProvider


class AdzunaProvider(JobProvider):
    name = "adzuna"
    base_url = "https://api.adzuna.com/v1/api/jobs"
    country = "gb"
    results_per_page = 20

    def __init__(self) -> None:
        self.app_id = os.getenv("ADZUNA_APP_ID") or os.getenv("adzuna_app_id")
        self.api_key = os.getenv("ADZUNA_API_KEY") or os.getenv("adzuna_api_key")

    def search_jobs(
        self, role: str, location: str | None = None, **kwargs
    ) -> list[JobOpportunity]:
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

        data = self._get_json(
            url, params=params, headers={"Accept": "application/json"}
        )
        return self._map_items(data.get("results", []))

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