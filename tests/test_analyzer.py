import json

import pytest

from analyzer_agent.cv_analyzer import CVAnalyzer
from analyzer_agent.errors import AnalysisValidationError, InvalidJSONError
from analyzer_agent.providers import LLMProvider


class FakeProvider(LLMProvider):
    def __init__(self, content: str) -> None:
        self._content = content

    def generate_json(self, prompt: str) -> str:
        return self._content


def _analysis_data() -> dict:
    return {
        "RECRUITMENT_REPORT": {
            "BEST_FIT_JOB_POSITIONS": [
                {"rank": i + 1, "position": "Role", "match_explanation": "x"}
                for i in range(20)
            ],
            "ATS_KEYWORDS": {
                "technical_skills": ["python"],
                "tools_and_technologies": ["docker"],
                "professional_skills": ["leadership"],
                "ai_data_keywords": ["ml"],
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


def test_analyze_returns_valid_analysis():
    provider = FakeProvider(json.dumps(_analysis_data()))
    analysis = CVAnalyzer(provider=provider).analyze("resume text")

    assert len(analysis.RECRUITMENT_REPORT.BEST_FIT_JOB_POSITIONS) == 20
    assert analysis.RECRUITMENT_REPORT.RESUME_SCORE.overall_score == 7.5


def test_analyze_invalid_json_raises_invalid_json_error():
    provider = FakeProvider("{not valid json")
    with pytest.raises(InvalidJSONError):
        CVAnalyzer(provider=provider).analyze("resume text")


def test_analyze_validation_violation_raises_validation_error():
    data = _analysis_data()
    data["RECRUITMENT_REPORT"]["BEST_FIT_JOB_POSITIONS"] = (
        data["RECRUITMENT_REPORT"]["BEST_FIT_JOB_POSITIONS"][:1]
    )
    provider = FakeProvider(json.dumps(data))
    with pytest.raises(AnalysisValidationError):
        CVAnalyzer(provider=provider).analyze("resume text")


def test_analyze_builds_prompt_with_resume_text():
    seen = {}

    class CapturingProvider(LLMProvider):
        def generate_json(self, prompt: str) -> str:
            seen["prompt"] = prompt
            return json.dumps(_analysis_data())

    CVAnalyzer(provider=CapturingProvider()).analyze("MY CANDIDATE CV")

    assert "RECRUITMENT REPORT STRUCTURE" in seen["prompt"]
    assert "MY CANDIDATE CV" in seen["prompt"]
    assert seen["prompt"].endswith("MY CANDIDATE CV")