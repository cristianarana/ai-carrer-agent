from pypdf import PdfReader

from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis
from job_search_agent.interface.job_match import (
    JobMatch,
    JobSearchOutcome,
    JobSearchSummary,
)
from job_search_agent.interface.job_opportunity import JobOpportunity
from pdf_report.generate_report import ReportGenerator


def _analysis_data(name=None, title=None) -> dict:
    return {
        "CANDIDATE_PROFILE": {"name": name, "professional_title": title},
        "RECRUITMENT_REPORT": {
            "BEST_FIT_JOB_POSITIONS": [
                {"rank": i + 1, "position": f"Position {i}", "match_explanation": "x"}
                for i in range(20)
            ],
            "ATS_KEYWORDS": {
                "technical_skills": ["python", "fastapi"],
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
                "explanation": "A solid profile with room to grow.",
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


def _analysis(name=None, title=None) -> CVAnalysis:
    return CVAnalysis.model_validate(_analysis_data(name, title))


def _outcome() -> JobSearchOutcome:
    job = JobOpportunity(
        title="Senior Backend Engineer",
        description="Backend role using python and docker.",
        requirements=["python", "docker"],
        location="Remote",
        company="Acme Corp",
        salary_range="USD 80000 - 100000",
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
        matched_jobs=[JobMatch(job=job, position="Position 0", match_score=0.95)],
    )


def _pdf_text(path) -> list[str]:
    reader = PdfReader(str(path))
    return [page.extract_text() or "" for page in reader.pages]


def test_generate_report_basic_structure(tmp_path):
    out = tmp_path / "report.pdf"
    generator = ReportGenerator()
    path = generator.generate(
        analysis=_analysis("Cristian Arana", "Backend Software Engineer"),
        job_search=_outcome(),
        output_path=out,
    )

    assert path == out
    raw = out.read_bytes()
    assert raw.startswith(b"%PDF")
    assert len(raw) > 5000

    pages = _pdf_text(out)
    assert len(pages) >= 4
    assert "Cristian Arana" in pages[0]
    assert "Análisis de Curriculum" in pages[1]
    assert "Analizador de mercado laboral" in pages[-1]


def test_generate_report_cover_fallback_when_title_missing(tmp_path):
    out = tmp_path / "report.pdf"
    generator = ReportGenerator()
    generator.generate(
        analysis=_analysis("Cristian Arana", None),
        job_search=_outcome(),
        output_path=out,
    )

    pages = _pdf_text(out)
    assert "Informe general de Curriculum" in pages[0]
    assert "Position 0" in pages[0]


def test_generate_report_cover_fallback_when_both_missing(tmp_path):
    out = tmp_path / "report.pdf"
    generator = ReportGenerator()
    generator.generate(
        analysis=_analysis(None, None),
        job_search=_outcome(),
        output_path=out,
    )

    pages = _pdf_text(out)
    assert "Informe general de Curriculum" in pages[0]
    assert "Análisis de Curriculum" in pages[1]


def test_generate_report_job_table_columns(tmp_path):
    out = tmp_path / "report.pdf"
    generator = ReportGenerator()
    generator.generate(
        analysis=_analysis("Cristian Arana", "Backend Software Engineer"),
        job_search=_outcome(),
        output_path=out,
    )

    last = " ".join((_pdf_text(out)[-1] or "").split())
    for expected in ("Posición objetivo", "Empresa", "Ubicación", "Match", "Postular"):
        assert expected in last
    assert "Acme Corp" in last
    assert "remotive" in last