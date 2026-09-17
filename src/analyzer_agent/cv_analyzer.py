import json
import logging
import re
from pathlib import Path

from pydantic import ValidationError

from .errors import AnalysisValidationError, InvalidJSONError, ResumeTooLargeError
from .interfaces.ai_analyzer_response import CVAnalysis
from .providers import LLMProvider
from .validation import CVAnalysisValidator

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = Path(__file__).parent / "prompts" / "resume_analysis.txt"
_REPAIR_TEMPLATE = Path(__file__).parent / "prompts" / "repair_analysis.txt"

_REPAIR_MAX_PREVIOUS_CHARS = 4_000
_REPAIR_MAX_ERRORS_CHARS = 4_000


class CVAnalyzer:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        max_attempts: int = 3,
        max_resume_chars: int = 60_000,
    ) -> None:
        self._provider = provider
        self._max_attempts = max_attempts
        self._max_resume_chars = max_resume_chars

    def analyze(self, resume_text: str) -> CVAnalysis:
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
                    formatted_errors[:300],
                )

        assert last_error is not None
        raise last_error

    @staticmethod
    def _build_prompt(resume_text: str) -> str:
        template = _PROMPT_TEMPLATE.read_text(encoding="utf-8")
        return template.replace("{resume}", resume_text)

    @classmethod
    def _build_repair_prompt(cls, *, errors: str, previous_content: str) -> str:
        template = _REPAIR_TEMPLATE.read_text(encoding="utf-8")
        return (
            template.replace("{errors}", errors[:_REPAIR_MAX_ERRORS_CHARS])
            .replace("{previous_content}", previous_content[:_REPAIR_MAX_PREVIOUS_CHARS])
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