from pydantic import BaseModel

from job_search_agent.interface.job_match import JobSearchOutcome


class JobMatchRow(BaseModel):
    role: str
    title: str
    company: str
    location: str
    salary_range: str | None = None
    employment_type: str | None = None
    posted_date: str | None = None
    match_score: float
    source_provider: str | None = None
    apply_url: str | None = None


def build_job_rows(outcome: JobSearchOutcome) -> list[JobMatchRow]:
    return [
        JobMatchRow(
            role=match.position,
            title=match.job.title,
            company=match.job.company,
            location=match.job.location,
            salary_range=match.job.salary_range,
            employment_type=match.job.employment_type,
            posted_date=match.job.posted_date,
            match_score=match.match_score,
            source_provider=match.job.source_provider,
            apply_url=match.job.apply_url,
        )
        for match in outcome.matched_jobs
    ]