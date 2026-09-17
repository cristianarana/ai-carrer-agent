from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis
from job_search_agent.interface.job_match import (
    JobMatch,
    JobSearchOutcome,
    JobSearchSummary,
)
from job_search_agent.interface.job_opportunity import JobOpportunity
from pdf_report.interface.job_market_row import build_job_rows


def _analysis() -> CVAnalysis:
    data = {
        "CANDIDATE_PROFILE": {
            "name": "Cristian Arana",
            "professional_title": "Backend Software Engineer",
        },
        "RECRUITMENT_REPORT": {
            "BEST_FIT_JOB_POSITIONS": [
                {"rank": i + 1, "position": "Backend Engineer", "match_explanation": "x"}
                for i in range(20)
            ],
            "ATS_KEYWORDS": {
                "technical_skills": ["python"],
                "tools_and_technologies": ["docker"],
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
        },
    }
    return CVAnalysis.model_validate(data)


def _outcome() -> JobSearchOutcome:
    job = JobOpportunity(
        title="Senior Backend Engineer",
        description="Backend role using python and docker.",
        requirements=["python", "docker"],
        location="Remote",
        company="Acme",
        salary_range="$80k - $100k",
        employment_type="full_time",
        posted_date="2026-01-10",
        apply_url="https://example.com/apply",
        source_provider="remotive",
    )
    return JobSearchOutcome(
        analysis=_analysis(),
        summary=JobSearchSummary(
            total_roles_searched=20,
            total_jobs_found=1,
            total_matched_jobs=1,
            attempted_providers=["remotive"],
        ),
        matched_jobs=[JobMatch(job=job, position="Backend Engineer", match_score=0.95)],
    )


def test_build_job_rows_maps_all_attributes():
    rows = build_job_rows(_outcome())
    assert len(rows) == 1
    row = rows[0]
    assert row.role == "Backend Engineer"
    assert row.title == "Senior Backend Engineer"
    assert row.company == "Acme"
    assert row.location == "Remote"
    assert row.salary_range == "$80k - $100k"
    assert row.employment_type == "full_time"
    assert row.posted_date == "2026-01-10"
    assert row.match_score == 0.95
    assert row.source_provider == "remotive"
    assert row.apply_url == "https://example.com/apply"


def test_build_job_rows_empty_outcome():
    outcome = JobSearchOutcome(analysis=_analysis())
    assert build_job_rows(outcome) == []