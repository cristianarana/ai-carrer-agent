import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "report_structure" / "pages"
STYLE_DIR = BASE_DIR / "report_structure" / "style"

_DEFAULT_COVER_TITLE = "Informe general de Curriculum"

_SCORE_LABELS = [
    ("relevance_to_target_positions", "Relevancia para posiciones objetivo"),
    ("technical_skills", "Habilidades técnicas"),
    ("professional_experience", "Experiencia profesional"),
    ("achievement_oriented_descriptions", "Descripciones orientadas a logros"),
    ("ats_optimization", "Optimización ATS"),
    ("clarity_and_structure", "Claridad y estructura"),
    ("seniority_positioning", "Posicionamiento de seniority"),
]

_IMPROVEMENT_CATEGORIES = [
    ("immediate_actions", "Acciones inmediatas"),
    ("technical_enhancements", "Mejoras técnicas"),
    ("ats_optimization", "Optimización ATS"),
    ("professional_and_structural_improvements", "Mejoras profesionales y estructurales"),
    ("long_term_improvements", "Mejoras a largo plazo"),
]


def _ensure_windows_gtk() -> None:
    if os.name != "nt":
        return
    candidates = [
        os.environ.get("GTK_BIN"),
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files\gtk3-runtime\bin",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_dir():
            if candidate not in os.environ.get("PATH", ""):
                os.environ["PATH"] = candidate + os.pathsep + os.environ["PATH"]
            return


_ensure_windows_gtk()

import jinja2  # noqa: E402
import weasyprint  # noqa: E402

from analyzer_agent.interfaces.ai_analyzer_response import CVAnalysis  # noqa: E402
from job_search_agent.interface.job_match import JobSearchOutcome  # noqa: E402

from .interface.job_market_row import build_job_rows  # noqa: E402

_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(PAGES_DIR)),
    autoescape=True,
)


class ReportGenerator:
    @staticmethod
    def _render(template_name: str, **context) -> str:
        return _environment.get_template(template_name).render(**context)

    def generate(
        self,
        *,
        analysis: CVAnalysis,
        job_search: JobSearchOutcome,
        output_path: str | Path,
    ) -> Path:
        pages = self._build_pages(analysis, job_search)
        document = self._render("base.html.j2", **pages)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        weasyprint.HTML(string=document, base_url=str(STYLE_DIR)).write_pdf(str(path))
        return path

    @classmethod
    def _build_pages(cls, analysis: CVAnalysis, job_search: JobSearchOutcome) -> dict:
        candidate = analysis.CANDIDATE_PROFILE
        report = analysis.RECRUITMENT_REPORT

        cover_title = (
            candidate.name
            if candidate.name and candidate.professional_title
            else _DEFAULT_COVER_TITLE
        )
        cover_subtitle = candidate.professional_title or (
            report.BEST_FIT_JOB_POSITIONS[0].position
        )

        score = report.RESUME_SCORE
        breakdown = score.breakdown

        improvements = [
            (
                getattr(report.HOW_TO_REACH_10, field),
                label,
            )
            for field, label in _IMPROVEMENT_CATEGORIES
        ]

        return {
            "cover": cls._render(
                "cover.html.j2",
                cover_title=cover_title,
                cover_subtitle=cover_subtitle,
            ),
            "analysis": cls._render(
                "analysis.html.j2",
                best_fit=report.BEST_FIT_JOB_POSITIONS,
                ats=report.ATS_KEYWORDS,
                recruiter=report.TEN_SECOND_RECRUITER_TEST,
                score=score,
                score_breakdown=[
                    (label, getattr(breakdown, field))
                    for field, label in _SCORE_LABELS
                ],
                improvements=improvements,
            ),
            "job_market": cls._render(
                "job_market.html.j2",
                summary=job_search.summary,
                rows=build_job_rows(job_search),
            ),
        }