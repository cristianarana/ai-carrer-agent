import json
import logging
import re
from pathlib import Path

from pydantic import ValidationError

from core.config import load_settings
from .errors import (
    AnalysisValidationError,
    EmptyResumeError,
    InvalidJSONError,
    ResumeTooLargeError,
)
from .interfaces.ai_analyzer_response import CVAnalysis
from .providers import LLMProvider
from .validation import CVAnalysisValidator

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = Path(__file__).parent / "prompts" / "resume_analysis.txt"
_REPAIR_TEMPLATE = Path(__file__).parent / "prompts" / "repair_analysis.txt"


class CVAnalyzer:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        max_attempts: int | None = None,
        max_resume_chars: int | None = None,
        repair_max_previous_chars: int | None = None,
        repair_max_errors_chars: int | None = None,
        log_sample_chars: int | None = None,
    ) -> None:
        settings = load_settings()
        self._provider = provider
        self._max_attempts = (
            max_attempts if max_attempts is not None else settings.analyzer_max_attempts
        )
        self._max_resume_chars = (
            max_resume_chars
            if max_resume_chars is not None
            else settings.max_resume_chars
        )
        self._repair_max_previous_chars = (
            repair_max_previous_chars
            if repair_max_previous_chars is not None
            else settings.analyzer_repair_max_previous_chars
        )
        self._repair_max_errors_chars = (
            repair_max_errors_chars
            if repair_max_errors_chars is not None
            else settings.analyzer_repair_max_errors_chars
        )
        self._log_sample_chars = (
            log_sample_chars
            if log_sample_chars is not None
            else settings.analyzer_log_sample_chars
        )

    def analyze(self, resume_text: str) -> CVAnalysis:
        if not resume_text.strip() or not any(
            ch.isalnum() for ch in resume_text
        ):
            raise EmptyResumeError(
                "The resume text is empty or contains no textual content"
            )
        if len(resume_text) > self._max_resume_chars:
            raise ResumeTooLargeError(len(resume_text), self._max_resume_chars)

        last_error: Exception | None = None
        formatted_errors = ""
        previous_content = ""

        for attempt in range(self._max_attempts):
            if attempt == 0:
                prompt = self._build_prompt(resume_text)
            else:
                prompt = self._build_repair_prompt(
                    errors=formatted_errors, previous_content=previous_content
                )

            previous_content = self._provider.generate_json(prompt)

            try:
                data = self._extract_json(previous_content)
                analysis = CVAnalysis.model_validate(data)
                CVAnalysisValidator.validate(analysis)
                logger.info(
                    "LLM analysis OK (attempt %d/%d) content_chars=%d",
                    attempt + 1,
                    self._max_attempts,
                    len(previous_content),
                )
                return analysis
            except (InvalidJSONError, ValidationError, ValueError) as exc:
                if isinstance(exc, InvalidJSONError):
                    last_error = exc
                else:
                    last_error = AnalysisValidationError(str(exc))
                formatted_errors = self._format_errors(exc)
                logger.warning(
                    "LLM analysis failed, attempt %d/%d: %s",
                    attempt + 1,
                    self._max_attempts,
                    formatted_errors[: self._log_sample_chars],
                )
                logger.debug(
                    "LLM raw content (sample %d chars): %r",
                    self._log_sample_chars,
                    previous_content[: self._log_sample_chars],
                )

        assert last_error is not None
        raise last_error

    @staticmethod
    def _build_prompt(resume_text: str) -> str:
        template = _PROMPT_TEMPLATE.read_text(encoding="utf-8")
        return template.replace("{resume}", resume_text)

    def _build_repair_prompt(self, *, errors: str, previous_content: str) -> str:
        template = _REPAIR_TEMPLATE.read_text(encoding="utf-8")
        return (
            template.replace("{errors}", errors[: self._repair_max_errors_chars])
            .replace(
                "{previous_content}",
                previous_content[: self._repair_max_previous_chars],
            )
        )

    @staticmethod
    def _extract_json(content: str) -> dict:
        text = content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise InvalidJSONError("LLM returned invalid JSON") from exc

    @staticmethod
    def _format_errors(exc: Exception) -> str:
        if isinstance(exc, ValidationError):
            return "\n".join(
                f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
            )
        return str(exc)