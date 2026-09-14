import re
from html import unescape

from ..interface.job_opportunity import JobOpportunity
from .base_provider import JobProvider


class RemotiveProvider(JobProvider):
    name = "remotive"
    base_url = "https://remotive.com/api/remote-jobs"

    def search_jobs(
        self, role: str, location: str | None = None, **kwargs
    ) -> list[JobOpportunity]:
        params: dict[str, str] = {}
        if role:
            params["search"] = role
        for key in ("category", "company_name", "limit"):
            if kwargs.get(key):
                params[key] = str(kwargs[key])

        data = self._get_json(self.base_url, params=params)
        return self._map_items(data.get("jobs", []))

    def _map_job(self, item: dict) -> JobOpportunity:
        return JobOpportunity(
            title=item.get("title", ""),
            description=self._html_to_text(item.get("description", "")),
            requirements=item.get("tags", []),
            location=item.get("candidate_required_location", ""),
            company=item.get("company_name", ""),
            salary_range=item.get("salary"),
            employment_type=item.get("job_type"),
            posted_date=item.get("publication_date"),
            company_url=item.get("company_logo"),
            apply_url=item.get("url"),
        )

    @staticmethod
    def _html_to_text(html: str) -> str:
        text = re.sub(r"<[^>]+>", " ", html)
        return " ".join(unescape(text).split())