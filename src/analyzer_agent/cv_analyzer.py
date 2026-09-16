import json
from pathlib import Path

from pydantic import ValidationError

from .errors import AnalysisValidationError, InvalidJSONError
from .interfaces.ai_analyzer_response import CVAnalysis
from .providers import LLMProvider
from .validation import CVAnalysisValidator

_PROMPT_TEMPLATE = Path(__file__).parent / "prompts" / "resume_analysis.txt"


class CVAnalyzer:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def analyze(self, resume_text: str) -> CVAnalysis:
        prompt = self._build_prompt(resume_text)

        content = self._provider.generate_json(prompt)
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise InvalidJSONError("LLM returned invalid JSON") from exc

        try:
            analysis = CVAnalysis.model_validate(data)
            CVAnalysisValidator.validate(analysis)
        except (ValidationError, ValueError) as exc:
            raise AnalysisValidationError(str(exc)) from exc

        return analysis

    @staticmethod
    def _build_prompt(resume_text: str) -> str:
        template = _PROMPT_TEMPLATE.read_text(encoding="utf-8")
        return template.replace("{resume}", resume_text)