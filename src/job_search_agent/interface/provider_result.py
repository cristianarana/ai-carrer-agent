from pydantic import BaseModel, Field

from .discarded_job import DiscardedJob
from .job_opportunity import JobOpportunity


class ProviderSearchResult(BaseModel):
    provider: str
    jobs: list[JobOpportunity] = Field(default_factory=list)
    discarded_jobs: list[DiscardedJob] = Field(default_factory=list)