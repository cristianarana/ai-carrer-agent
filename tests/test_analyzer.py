import json

import pytest

from analyzer_agent.cv_analyzer import CVAnalyzer
from analyzer_agent.errors import (
    AnalysisValidationError,
    InvalidJSONError,
    ResumeTooLargeError,
)
from analyzer_agent.providers import LLMProvider


class FakeProvider(LLMProvider):
    def __init__(self, content: str) -> None:
        self._content = content

    def generate_json(self, prompt: str) -> str:
        return self._content


def _analysis_data() -> dict:
    return {
        "CANDIDATE_PROFILE": {
            "name": "Cristian Arana",
            "professional_title": "Backend Software Engineer",
        },
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


def test_analyze_resume_exceeding_limit_raises_and_skips_provider():
    calls = []

    class CountingProvider(LLMProvider):
        def generate_json(self, prompt: str) -> str:
            calls.append(prompt)
            return json.dumps(_analysis_data())

    analyzer = CVAnalyzer(provider=CountingProvider(), max_resume_chars=10)

    with pytest.raises(ResumeTooLargeError):
        analyzer.analyze("x" * 11)

    assert calls == []


def test_analyze_resume_within_limit_ok(capsys):
    provider = FakeProvider(json.dumps(_analysis_data()))
    result = CVAnalyzer(provider=provider).analyze("x" * 10)
    assert result.RECRUITMENT_REPORT.RESUME_SCORE.overall_score == 7.5


def test_analyze_repair_on_second_attempt_without_resume():
    seen = []

    class RepairingProvider(LLMProvider):
        def generate_json(self, prompt: str) -> str:
            seen.append(prompt)
            if len(seen) == 1:
                data = _analysis_data()
                data["RECRUITMENT_REPORT"]["BEST_FIT_JOB_POSITIONS"] = data[
                    "RECRUITMENT_REPORT"
                ]["BEST_FIT_JOB_POSITIONS"][:1]
                return json.dumps(data)
            return json.dumps(_analysis_data())

    CVAnalyzer(provider=RepairingProvider(), max_attempts=3).analyze(
        "MY CANDIDATE CV"
    )

    assert len(seen) == 2
    assert "MY CANDIDATE CV" in seen[0]
    assert "MY CANDIDATE CV" not in seen[1]


def test_analyze_repair_prompt_contains_validation_errors():
    seen = []

    class RepairingProvider(LLMProvider):
        def generate_json(self, prompt: str) -> str:
            seen.append(prompt)
            if len(seen) == 1:
                data = _analysis_data()
                data["RECRUITMENT_REPORT"]["BEST_FIT_JOB_POSITIONS"] = data[
                    "RECRUITMENT_REPORT"
                ]["BEST_FIT_JOB_POSITIONS"][:1]
                return json.dumps(data)
            return json.dumps(_analysis_data())

    CVAnalyzer(provider=RepairingProvider(), max_attempts=2).analyze("CV")

    assert "VALIDATION ERRORS" in seen[1]
    assert "BEST_FIT_JOB_POSITIONS" in seen[1]


def test_extract_json_strips_code_fences():
    raw = "```json\n" + json.dumps(_analysis_data()) + "\n```"
    assert CVAnalyzer._extract_json(raw)["RECRUITMENT_REPORT"]["RESUME_SCORE"][
        "overall_score"
    ] == 7.5


def test_extract_json_surrounding_text():
    raw = "Sure, here you go: " + json.dumps(_analysis_data()) + " Regards"
    data = CVAnalyzer._extract_json(raw)
    assert data["RECRUITMENT_REPORT"]["RESUME_SCORE"]["overall_score"] == 7.5


def test_analyze_fenced_output_succeeds_first_attempt():
    seen = []

    class FencedProvider(LLMProvider):
        def generate_json(self, prompt: str) -> str:
            seen.append(prompt)
            return "```json\n" + json.dumps(_analysis_data()) + "\n```"

    CVAnalyzer(provider=FencedProvider()).analyze("CV")

    assert len(seen) == 1


def test_analyze_raises_after_exhausting_attempts():
    provider = FakeProvider("{not valid json")
    with pytest.raises(InvalidJSONError):
        CVAnalyzer(provider=provider, max_attempts=3).analyze("CV")


def test_candidate_profile_empty_values_normalized_to_none():
    from analyzer_agent.interfaces.candidate_profile import CandidateProfile

    profile = CandidateProfile.model_validate(
        {"name": "   ", "professional_title": ""}
    )
    assert profile.name is None
    assert profile.professional_title is None


def test_candidate_profile_validation_short_name_raises():
    from analyzer_agent.validation import CVAnalysisValidator
    from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis

    data = _analysis_data()
    data["CANDIDATE_PROFILE"] = {"name": "A", "professional_title": "Dev"}
    analysis = CVAnalysis.model_validate(data)
    with pytest.raises(ValueError, match="CANDIDATE_PROFILE.name"):
        CVAnalysisValidator.validate(analysis)


def test_candidate_profile_missing_raises_validation_error():
    from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis

    data = _analysis_data()
    del data["CANDIDATE_PROFILE"]
    with pytest.raises(Exception) as exc_info:
        CVAnalysis.model_validate(data)
    assert "CANDIDATE_PROFILE" in str(exc_info.value)


def test_empty_resume_raises():
    from analyzer_agent.errors import EmptyResumeError

    with pytest.raises(EmptyResumeError):
        CVAnalyzer(provider=FakeProvider("{}")).analyze("")


def test_whitespace_only_resume_raises():
    from analyzer_agent.errors import EmptyResumeError

    with pytest.raises(EmptyResumeError):
        CVAnalyzer(provider=FakeProvider("{}")).analyze("   \n\t  ")


def test_resume_without_text_content_raises():
    from analyzer_agent.errors import EmptyResumeError

    with pytest.raises(EmptyResumeError):
        CVAnalyzer(provider=FakeProvider("{}")).analyze("--- *** ###")


def test_valid_resume_does_not_raise_empty_error():
    provider = FakeProvider(json.dumps(_analysis_data()))
    analysis = CVAnalyzer(provider=provider).analyze("Sensible resume content")
    assert analysis.CANDIDATE_PROFILE is not None