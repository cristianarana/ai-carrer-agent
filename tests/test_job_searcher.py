import pytest

from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis
from job_search_agent.helper.keyword_scorer import KeywordScorer
from job_search_agent.interface.job_opportunity import JobOpportunity
from job_search_agent.interface.provider_result import ProviderSearchResult
from job_search_agent.job_searcher import JobSearcher
from job_search_agent.provider.base_provider import ProviderError


def _analysis() -> CVAnalysis:
    data = {
        "RECRUITMENT_REPORT": {
            "BEST_FIT_JOB_POSITIONS": [
                {"rank": i + 1, "position": "Backend Engineer", "match_explanation": "x"}
                for i in range(20)
            ],
            "ATS_KEYWORDS": {
                "technical_skills": ["python", "nestjs"],
                "tools_and_technologies": ["docker", "postgresql"],
                "professional_skills": ["leadership"],
                "ai_data_keywords": ["llm"],
            },
            "TEN_SECOND_RECRUITER_TEST": {
                "positive": ["a", "b", "c"],
                "unclear_or_weak": ["d", "e", "f"],
                "could_cause_rejection": ["g", "h", "i"],
            },
            "RESUME_SCORE": {
                "overall_score": 7.5,
                "explanation": "ok",
                "breakdown": {
                    "relevance_to_target_positions": 7,
                    "technical_skills": 7,
                    "professional_experience": 7,
                    "achievement_oriented_descriptions": 7,
                    "ats_optimization": 7,
                    "clarity_and_structure": 7,
                    "seniority_positioning": 7,
                },
            },
            "HOW_TO_REACH_10": {
                "immediate_actions": [
                    {"priority": "High", "impact": f"a{i}"} for i in range(3)
                ],
                "technical_enhancements": [
                    {"priority": "Medium", "impact": f"b{i}"} for i in range(3)
                ],
                "ats_optimization": [
                    {"priority": "High", "impact": f"c{i}"} for i in range(3)
                ],
                "professional_and_structural_improvements": [
                    {"priority": "Low", "impact": f"d{i}"} for i in range(2)
                ],
                "long_term_improvements": [
                    {"priority": "Medium", "impact": f"e{i}"} for i in range(2)
                ],
            },
        }
    }
    return CVAnalysis.model_validate(data)


class FakeProvider:
    def __init__(
        self,
        name: str,
        jobs: list[JobOpportunity] | None = None,
        *,
        configured: bool = True,
        error: ProviderError | None = None,
    ) -> None:
        self.name = name
        self.config_required: tuple[str, ...] = ("FAKE_KEY",)
        self._jobs = jobs or []
        self._configured = configured
        self._error = error

    def is_configured(self) -> bool:
        return self._configured

    def search_jobs(self, role: str, location: str | None = None, **kwargs):
        if self._error:
            raise self._error
        return ProviderSearchResult(
            provider=self.name, jobs=self._jobs, discarded_jobs=[]
        )


def _job(title: str = "Backend Engineer", *, company: str = "Acme", location: str = "Remote"):
    return JobOpportunity(
        title=title,
        description=(
            "Building REST APIs with python, nestjs, docker and postgresql; "
            "leadership and LLM skills."
        ),
        requirements=["python", "docker"],
        location=location,
        company=company,
        apply_url=f"https://example.com/jobs/{title.lower().replace(' ', '-')}",
        source_provider="fake",
    )


class MapScorer:
    def __init__(self, scores: dict[str, float]) -> None:
        self._scores = scores

    def score(self, *, job, position, keywords) -> float:
        return self._scores.get(job.title, 0.0)


def test_outcome_returns_analysis_untouched():
    analysis = _analysis()
    outcome = JobSearcher(providers=[FakeProvider("fake_a", [_job()])]).search(analysis)
    assert outcome.analysis is analysis


def test_filters_jobs_below_threshold_and_sorts():
    jobs = [_job("High A"), _job("Low"), _job("High B")]
    providers = [FakeProvider("fake_a", jobs)]
    scorer = MapScorer({"High A": 0.90, "Low": 0.80, "High B": 0.95})

    outcome = JobSearcher(providers=providers, scorer=scorer).search(_analysis())

    titles = [m.job.title for m in outcome.matched_jobs]
    assert titles == ["High B", "High A"]
    assert all(m.match_score >= 0.85 for m in outcome.matched_jobs)


def test_match_score_rounded_to_three_decimals():
    jobs = [_job("Backend Engineer")]
    providers = [FakeProvider("fake_a", jobs)]

    outcome = JobSearcher(
        providers=providers, scorer=MapScorer({"Backend Engineer": 0.8546})
    ).search(_analysis())

    assert outcome.matched_jobs[0].match_score == 0.855


def test_dedupes_same_job_between_providers():
    job = _job()
    providers = [FakeProvider("fake_a", [job]), FakeProvider("fake_b", [job])]
    outcome = JobSearcher(providers=providers).search(_analysis())
    assert len(outcome.matched_jobs) == 1


def test_provider_error_is_collected_and_search_continues():
    broken = FakeProvider("fake_broken", error=ProviderError("fake_broken", "down", status_code=500))
    ok = FakeProvider("fake_ok", [_job()])
    outcome = JobSearcher(providers=[broken, ok]).search(_analysis())

    assert [m.job.title for m in outcome.matched_jobs] == ["Backend Engineer"]
    assert outcome.searches[0].errors["fake_broken"] == "fake_broken error: down"


def test_unconfigured_provider_is_skipped_without_calls():
    configured = FakeProvider("fake_ok", [_job()])
    skipped = FakeProvider("fake_skipped", configured=False)
    outcome = JobSearcher(providers=[configured, skipped]).search(_analysis())

    assert [m.job.title for m in outcome.matched_jobs] == ["Backend Engineer"]
    assert "fake_skipped" in outcome.searches[0].skipped_providers


def test_keyword_scorer_matches_full_profile():
    analysis = _analysis()
    analysis.RECRUITMENT_REPORT.BEST_FIT_JOB_POSITIONS[0].rank = 1
    job = JobOpportunity(
        title="Senior Backend Engineer",
        description="REST APIs with python, nestjs, docker, postgresql and LLM integrations.",
        requirements=["python", "nestjs", "docker", "postgresql", "llm"],
        location="Remote",
        company="Acme",
        apply_url="https://example.com/jobs/senior",
        source_provider="fake_a",
    )
    provider = FakeProvider("fake_a", [job])
    outcome = JobSearcher(providers=[provider]).search(analysis)

    assert len(outcome.matched_jobs) == 1
    assert outcome.matched_jobs[0].job.source_provider == "fake_a"
    assert outcome.matched_jobs[0].position == "Backend Engineer"


def test_keyword_scorer_rejects_unrelated_job():
    job = JobOpportunity(
        title="Accountant",
        description="Bookkeeping and tax reporting.",
        requirements=["spreadsheets"],
        location="Remote",
        company="Acme",
        apply_url="https://example.com/jobs/accountant",
    )
    provider = FakeProvider("fake_a", [job])
    outcome = JobSearcher(providers=[provider]).search(_analysis())
    assert outcome.matched_jobs == []