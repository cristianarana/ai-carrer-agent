from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .discarded_job import DiscardedJob
from .job_opportunity import JobOpportunity


class SearchReport(BaseModel):
    role: str
    location: str | None = None
    jobs: list[JobOpportunity] = Field(default_factory=list)
    discarded_jobs: dict[str, list[DiscardedJob]] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    skipped_providers: dict[str, str] = Field(default_factory=dict)
    attempted_providers: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))