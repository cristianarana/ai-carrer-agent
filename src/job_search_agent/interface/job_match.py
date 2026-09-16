from pydantic import BaseModel, Field

from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis
from .job_opportunity import JobOpportunity
from .search_report import SearchReport


class JobMatch(BaseModel):
    job: JobOpportunity
    position: str
    match_score: float = Field(ge=0.0, le=1.0)


class JobSearchSummary(BaseModel):
    total_roles_searched: int = 0
    total_jobs_found: int = 0
    total_matched_jobs: int = 0
    attempted_providers: list[str] = Field(default_factory=list)
    failed_providers: list[str] = Field(default_factory=list)
    skipped_providers: dict[str, str] = Field(default_factory=dict)
    had_errors: bool = False
    had_results: bool = False


class JobSearchOutcome(BaseModel):
    analysis: CVAnalysis
    matched_jobs: list[JobMatch] = Field(default_factory=list)
    searches: list[SearchReport] = Field(default_factory=list)
    summary: JobSearchSummary | None = None