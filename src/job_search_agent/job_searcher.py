from __future__ import annotations

import logging

from job_search_agent.errors import NoMatchesError
from job_search_agent.helper import KeywordScorer, MatchScorer
from job_search_agent.interface.job_match import (
    JobMatch,
    JobSearchOutcome,
    JobSearchSummary,
)
from job_search_agent.provider import get_providers, search_all
from job_search_agent.provider.base_provider import JobProvider

logger = logging.getLogger(__name__)


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
        outcome.summary = self._build_summary(outcome)

        if not outcome.matched_jobs:
            reason = (
                "no_jobs_found"
                if outcome.summary.total_jobs_found == 0
                else "none_above_threshold"
            )
            logger.warning("No matching jobs for the profile: %s", reason)
            raise NoMatchesError(outcome.summary, reason=reason)

        return outcome

    @staticmethod
    def _build_summary(outcome: JobSearchOutcome) -> JobSearchSummary:
        attempted: set[str] = set()
        failed: set[str] = set()
        skipped: dict[str, str] = {}
        unique_jobs: set[tuple[str, str, str]] = set()

        for sr in outcome.searches:
            attempted.update(sr.attempted_providers)
            failed.update(sr.errors)
            for name, reason in sr.skipped_providers.items():
                skipped.setdefault(name, reason)
            for job in sr.jobs:
                unique_jobs.add(
                    (job.title.lower(), job.company.lower(), job.location.lower())
                )

        return JobSearchSummary(
            total_roles_searched=len(outcome.searches),
            total_jobs_found=len(unique_jobs),
            total_matched_jobs=len(outcome.matched_jobs),
            attempted_providers=sorted(attempted),
            failed_providers=sorted(failed),
            skipped_providers=skipped,
            had_errors=bool(failed),
            had_results=bool(outcome.matched_jobs),
        )