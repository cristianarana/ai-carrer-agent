from pathlib import Path

import pytest

from job_search_agent.errors import NoMatchesError
from job_search_agent.interface.job_opportunity import JobOpportunity
from job_search_agent.interface.provider_result import ProviderSearchResult
from pipelines.job_hunter import JobHunterPipeline

from helpers import build_analysis


class StubAnalyzer:
    def __init__(self, analysis=None, error=None) -> None:
        self.analysis = analysis or build_analysis()
        self.error = error
        self.seen_texts: list[str] = []

    def analyze(self, resume_text: str):
        self.seen_texts.append(resume_text)
        if self.error:
            raise self.error
        return self.analysis


class FakeJobProvider:
    name = "fake"
    config_required = ("FAKE_KEY",)

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def is_configured(self) -> bool:
        return True

    def search_jobs(self, role: str, location: str | None = None, **kwargs):
        self.calls.append((role, location))
        return ProviderSearchResult(
            provider=self.name,
            jobs=[FakeJobProvider._job()],
            discarded_jobs=[],
        )

    @staticmethod
    def _job() -> JobOpportunity:
        return JobOpportunity(
            title="Backend Engineer",
            description="REST APIs with python, nestjs, docker and postgresql.",
            requirements=["python", "nestjs"],
            location="Remote",
            company="Acme",
            apply_url="https://example.com/jobs/1",
        )


class AlwaysScorer:
    def score(self, *, job, position, keywords) -> float:
        return 0.9


class ZeroScorer:
    def score(self, *, job, position, keywords) -> float:
        return 0.0


class StubGenerator:
    def generate(self, *, analysis, job_search, output_path) -> Path:
        return Path(output_path)


def test_pipeline_runs_linear_flow(tmp_path):
    analyzer = StubAnalyzer()
    provider = FakeJobProvider()
    generator = StubGenerator()
    output_path = tmp_path / "report.pdf"

    pipeline = JobHunterPipeline(
        analyzer=analyzer,
        providers=[provider],
        scorer=AlwaysScorer(),
        report_generator=generator,
    )
    result = pipeline.run(
        resume_text="MY CV",
        location="Remote",
        max_positions=3,
        output_path=output_path,
    )

    assert analyzer.seen_texts == ["MY CV"]
    assert provider.calls[0][1] == "Remote"
    assert result == output_path


def test_pipeline_propagates_no_matches_error(tmp_path):
    analyzer = StubAnalyzer()
    provider = FakeJobProvider()
    output_path = tmp_path / "report.pdf"

    pipeline = JobHunterPipeline(
        analyzer=analyzer,
        providers=[provider],
        scorer=ZeroScorer(),
        report_generator=StubGenerator(),
    )
    with pytest.raises(NoMatchesError):
        pipeline.run(
            resume_text="MY CV",
            location=None,
            max_positions=3,
            output_path=output_path,
        )


def test_pipeline_propagates_analysis_errors(tmp_path):
    from analyzer_agent.errors import AnalysisValidationError

    analyzer = StubAnalyzer(error=AnalysisValidationError("validation failed"))
    pipeline = JobHunterPipeline(
        analyzer=analyzer,
        report_generator=StubGenerator(),
    )
    with pytest.raises(AnalysisValidationError):
        pipeline.run(
            resume_text="MY CV",
            output_path=tmp_path / "report.pdf",
        )