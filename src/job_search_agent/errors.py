from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interface.job_match import JobSearchSummary


class JobSearchError(Exception):
    pass


class NoMatchesError(JobSearchError):
    def __init__(self, summary: "JobSearchSummary", *, reason: str) -> None:
        self.summary = summary
        self.reason = reason
        super().__init__(f"No matching jobs found: {reason}")