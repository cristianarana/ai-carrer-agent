import logging
import os
import time
from pathlib import Path

from analyzer_agent.cv_analyzer import CVAnalyzer
from analyzer_agent.providers import OpenRouterProvider
from core.config import Settings
from job_search_agent.interface.job_match import JobSearchOutcome
from job_search_agent.job_searcher import JobSearcher
from pdf_report.generate_report import ReportGenerator

logger = logging.getLogger(__name__)


class JobHunterPipeline:
    def __init__(
        self,
        *,
        analyzer=None,
        providers=None,
        scorer=None,
        report_generator=None,
        llm_model: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings
        self._analyzer = analyzer
        self._providers = providers
        self._scorer = scorer
        self._report_generator = report_generator
        default_model = os.getenv(
            "OPENROUTER_MODEL", "~deepseek/deepseek-flash-latest"
        )
        if llm_model:
            self._llm_model = llm_model
        elif settings is not None:
            self._llm_model = settings.llm_model or default_model
        else:
            self._llm_model = default_model

    def _build_analyzer(self) -> CVAnalyzer:
        settings = self._settings
        if settings is not None:
            return CVAnalyzer(
                provider=OpenRouterProvider(
                    model=self._llm_model,
                    timeout=settings.openrouter_timeout,
                    retries=settings.openrouter_retries,
                    backoff=settings.openrouter_backoff,
                    max_tokens=settings.openrouter_max_tokens,
                ),
                max_attempts=settings.analyzer_max_attempts,
                max_resume_chars=settings.max_resume_chars,
                repair_max_previous_chars=settings.analyzer_repair_max_previous_chars,
                repair_max_errors_chars=settings.analyzer_repair_max_errors_chars,
                log_sample_chars=settings.analyzer_log_sample_chars,
            )
        return CVAnalyzer(provider=OpenRouterProvider(model=self._llm_model))

    def run(
        self,
        *,
        resume_text: str,
        location: str | None = None,
        max_positions: int | None = None,
        output_path: str | Path,
    ) -> Path:
        started = time.perf_counter()
        logger.info(
            "pipeline start resume_chars=%d location=%s max_positions=%s",
            len(resume_text),
            location,
            max_positions,
        )
        analyzer = self._analyzer or self._build_analyzer()
        analysis = analyzer.analyze(resume_text)
        logger.info(
            "pipeline phase ok step=analysis elapsed=%.2fs", time.perf_counter() - started
        )

        searcher = JobSearcher(
            providers=self._providers,
            scorer=self._scorer,
            location=location,
            max_positions=max_positions,
            settings=self._settings,
        )
        outcome: JobSearchOutcome = searcher.search(analysis)
        logger.info(
            "pipeline phase ok step=search matched=%d elapsed=%.2fs",
            len(outcome.matched_jobs),
            time.perf_counter() - started,
        )

        report_generator = self._report_generator or ReportGenerator()
        result = report_generator.generate(
            analysis=analysis,
            job_search=outcome,
            output_path=output_path,
        )
        logger.info(
            "pipeline phase ok step=report path=%s elapsed=%.2fs",
            result,
            time.perf_counter() - started,
        )
        return result