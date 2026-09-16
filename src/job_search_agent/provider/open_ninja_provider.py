import os

from ..interface.job_opportunity import JobOpportunity
from ..interface.provider_result import ProviderSearchResult
from .base_provider import JobProvider


class OpenNinjaProvider(JobProvider):
    name = "open_ninja"
    base_url = "https://api.openwebninja.com/jsearch/search-v2"
    country = "us"
    language = "en"
    num_pages = 1
    config_required = ("OPEN_NINJA_API_KEY",)

    def __init__(self) -> None:
        self.api_key = os.getenv("OPEN_NINJA_API_KEY")

    def search_jobs(
        self, role: str, location: str | None = None, **kwargs
    ) -> ProviderSearchResult:
        query = f"{role} in {location}" if location else role
        params: dict = {
            "query": query,
            "country": kwargs.get("country", self.country),
            "language": kwargs.get("language", self.language),
            "num_pages": kwargs.get("num_pages", self.num_pages),
        }

        for key in (
            "cursor",
            "date_posted",
            "work_from_home",
            "employment_types",
            "job_requirements",
            "radius",
            "exclude_job_publishers",
            "fields",
        ):
            if key in kwargs:
                value = kwargs[key]
                params[key] = str(value).lower() if isinstance(value, bool) else value

        headers = {"x-api-key": self.api_key}
        data = self._get_json(self.base_url, params=params, headers=headers)
        payload = data.get("data") or {}
        jobs_data = payload.get("jobs", []) if isinstance(payload, dict) else payload
        jobs, discarded = self._map_items(jobs_data)
        return ProviderSearchResult(
            provider=self.name, jobs=jobs, discarded_jobs=discarded
        )

    def _map_job(self, item: dict) -> JobOpportunity:
        return JobOpportunity(
            title=item.get("job_title", ""),
            description=item.get("job_description", ""),
            requirements=self._build_requirements(item),
            location=self._build_location(item),
            company=item.get("employer_name", ""),
            salary_range=self._build_salary_range(
                item.get("job_min_salary"),
                item.get("job_max_salary"),
                item.get("job_salary_currency"),
                item.get("job_salary_period"),
            ),
            employment_type=item.get("job_employment_type"),
            posted_date=item.get("job_posted_at_datetime_utc"),
            company_url=item.get("employer_website"),
            apply_url=item.get("job_apply_link"),
        )

    @staticmethod
    def _build_requirements(item: dict) -> list[str]:
        highlights = (item.get("job_highlights") or {}).get("Qualifications")
        if highlights:
            return highlights
        return item.get("job_required_skills", [])

    @staticmethod
    def _build_location(item: dict) -> str:
        if item.get("job_is_remote") and not item.get("job_city"):
            return "Remote"
        parts = [
            part
            for part in (
                item.get("job_city"),
                item.get("job_state"),
                item.get("job_country"),
            )
            if part
        ]
        return ", ".join(dict.fromkeys(parts))