from typing import Protocol

from analyzer_agent.interfaces.ats_keywords import ATSKeywords
from analyzer_agent.interfaces.job_position import JobPosition
from job_search_agent.interface.job_opportunity import JobOpportunity


class MatchScorer(Protocol):
    def score(
        self, *, job: JobOpportunity, position: JobPosition, keywords: ATSKeywords
    ) -> float:
        ...