from pydantic import BaseModel, Field

from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis
from .job_opportunity import JobOpportunity
from .search_report import SearchReport


class JobMatch(BaseModel):
    job: JobOpportunity
    position: str
    match_score: float = Field(ge=0.0, le=1.0)


class JobSearchOutcome(BaseModel):
    analysis: CVAnalysis
    matched_jobs: list[JobMatch] = Field(default_factory=list)
    searches: list[SearchReport] = Field(default_factory=list)