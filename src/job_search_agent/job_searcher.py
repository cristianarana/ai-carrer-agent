from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from job_search_agent.errors import NoMatchesError
from job_search_agent.helper import KeywordScorer, MatchScorer
from job_search_agent.interface.job_match import (
    JobMatch,
    JobSearchOutcome,
    JobSearchSummary,
)
from job_search_agent.interface.job_opportunity import JobOpportunity
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
        max_positions: int | None = None,
        max_workers: int | None = None,
    ) -> None:
        self._providers = providers if providers is not None else get_providers()
        self._scorer = scorer or KeywordScorer()
        self._location = location
        self._max_positions = (
            max_positions
            if max_positions is not None
            else int(os.getenv("SEARCH_TOP_N", "5"))
        )
        self._max_workers = (
            max_workers
            if max_workers is not None
            else int(os.getenv("SEARCH_MAX_WORKERS", "4"))
        )

    def search(self, analysis) -> JobSearchOutcome:
        report = analysis.RECRUITMENT_REPORT
        keywords = report.ATS_KEYWORDS
        positions = report.BEST_FIT_JOB_POSITIONS[: self._max_positions]
        outcome = JobSearchOutcome(analysis=analysis)
        seen: set[tuple[str, str, str]] = set()

        per_position = [
            p
            for p in self._providers
            if self._search_mode(p) == "per_position"
        ]
        profile = [
            p for p in self._providers if self._search_mode(p) == "profile"
        ]

        if per_position and positions:
            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                reports = list(
                    pool.map(
                        lambda pos: self._search_role(pos, per_position),
                        positions,
                    )
                )
            for position, sr in zip(positions, reports):
                outcome.searches.append(sr)
                for job in sr.jobs:
                    self._consider(
                        job=job,
                        position=position,
                        keywords=keywords,
                        seen=seen,
                        outcome=outcome,
                    )

        broad_query = self._build_broad_query(positions, keywords)
        for provider in profile:
            sr = search_all(
                broad_query,
                location=self._location,
                providers=[provider],
            )
            outcome.searches.append(sr)
            for job in sr.jobs:
                self._consider_best(
                    job=job,
                    positions=positions,
                    keywords=keywords,
                    seen=seen,
                    outcome=outcome,
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

    def _search_role(self, position, providers: list[JobProvider]):
        return search_all(
            position.position,
            location=self._location,
            providers=providers,
        )

    @staticmethod
    def _search_mode(provider: JobProvider) -> str:
        return getattr(provider, "search_mode", "per_position")

    def _consider(
        self,
        *,
        job: JobOpportunity,
        position,
        keywords,
        seen: set[tuple[str, str, str]],
        outcome: JobSearchOutcome,
    ) -> None:
        key = self._dedup_key(job)
        if key in seen:
            return
        seen.add(key)
        score = self._scorer.score(
            job=job, position=position, keywords=keywords
        )
        if score >= self.MIN_MATCH:
            outcome.matched_jobs.append(
                JobMatch(
                    job=job,
                    position=position.position,
                    match_score=round(score, 3),
                )
            )

    def _consider_best(
        self,
        *,
        job: JobOpportunity,
        positions,
        keywords,
        seen: set[tuple[str, str, str]],
        outcome: JobSearchOutcome,
    ) -> None:
        key = self._dedup_key(job)
        if key in seen:
            return
        seen.add(key)
        best: tuple[float, object] | None = None
        for position in positions:
            score = self._scorer.score(
                job=job, position=position, keywords=keywords
            )
            if score >= self.MIN_MATCH and (
                best is None or score > best[0]
            ):
                best = (score, position)
        if best is not None:
            outcome.matched_jobs.append(
                JobMatch(
                    job=job,
                    position=best[1].position,
                    match_score=round(best[0], 3),
                )
            )

    @staticmethod
    def _dedup_key(job: JobOpportunity) -> tuple[str, str, str]:
        return (
            job.title.lower(),
            job.company.lower(),
            job.location.lower(),
        )

    @staticmethod
    def _build_broad_query(positions, keywords) -> str:
        parts: list[str] = []
        if positions:
            parts.append(positions[0].position)
        for field in ("technical_skills", "tools_and_technologies"):
            parts.extend(getattr(keywords, field, [])[:3])
        return " ".join(dict.fromkeys(parts)).strip()

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