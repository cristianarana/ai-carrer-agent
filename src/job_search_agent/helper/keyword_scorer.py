from analyzer_agent.interfaces.ats_keywords import ATSKeywords
from analyzer_agent.interfaces.job_position import JobPosition
from job_search_agent.interface.job_opportunity import JobOpportunity
from .match_scorer import MatchScorer


class KeywordScorer:
    _WEIGHTS = {
        "technical_skills": 1.0,
        "tools_and_technologies": 0.8,
        "ai_data_keywords": 1.0,
        "professional_skills": 0.6,
    }

    def score(
        self, *, job: JobOpportunity, position: JobPosition, keywords: ATSKeywords
    ) -> float:
        return 0.65 * self._keyword_match(job, keywords) + 0.35 * self._rank_match(position)

    def _keyword_match(self, job: JobOpportunity, keywords: ATSKeywords) -> float:
        haystack = " ".join(
            [job.title, job.company, job.location, " ".join(job.requirements), job.description]
        ).lower()
        found = total = 0.0
        for field, weight in self._WEIGHTS.items():
            for keyword in getattr(keywords, field):
                total += weight
                if keyword.lower() in haystack:
                    found += weight
        return found / total if total else 0.0

    @staticmethod
    def _rank_match(position: JobPosition) -> float:
        return (21 - position.rank) / 20