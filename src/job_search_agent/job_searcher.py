from __future__ import annotations

from job_search_agent.helper import KeywordScorer, MatchScorer
from job_search_agent.interface.job_match import JobMatch, JobSearchOutcome
from job_search_agent.provider import get_providers, search_all
from job_search_agent.provider.base_provider import JobProvider


class JobSearcher:
    MIN_MATCH = 0.85

    def __init__(
        self,
        providers: list[JobProvider] | None = None,
        scorer: MatchScorer | None = None,
        location: str | None = None,
    ) -> None:
        self._providers = providers if providers is not None else get_providers()
        self._scorer = scorer or KeywordScorer()
        self._location = location

    def search(self, analysis) -> JobSearchOutcome:
        report = analysis.RECRUITMENT_REPORT
        outcome = JobSearchOutcome(analysis=analysis)
        seen: set[tuple[str, str, str]] = set()

        for position in report.BEST_FIT_JOB_POSITIONS:
            sr = search_all(
                position.position, location=self._location, providers=self._providers
            )
            outcome.searches.append(sr)

            for job in sr.jobs:
                key = (job.title.lower(), job.company.lower(), job.location.lower())
                if key in seen:
                    continue
                seen.add(key)

                score = self._scorer.score(
                    job=job, position=position, keywords=report.ATS_KEYWORDS
                )
                if score >= self.MIN_MATCH:
                    outcome.matched_jobs.append(
                        JobMatch(
                            job=job,
                            position=position.position,
                            match_score=round(score, 3),
                        )
                    )

        outcome.matched_jobs.sort(key=lambda m: m.match_score, reverse=True)
        return outcome