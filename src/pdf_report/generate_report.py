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
from pypdf import PdfReader  # noqa: E402

from .errors import (
    InvalidOutputPathError,
    InvalidPDFOutputError,
    MissingReportDataError,
    PDFRenderError,
    ReportError,
)  # noqa: E402
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
        if not isinstance(analysis, CVAnalysis) or not isinstance(
            job_search, JobSearchOutcome
        ):
            raise MissingReportDataError(
                "A valid CVAnalysis and JobSearchOutcome are required to "
                "generate the report."
            )
        path = self._normalize_output_path(output_path)

        try:
            pages = self._build_pages(analysis, job_search)
            document = self._render("base.html.j2", **pages)
        except ReportError:
            raise
        except Exception as exc:
            raise PDFRenderError(f"Failed to render the report: {exc}") from exc

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise InvalidOutputPathError(
                f"Cannot create the report directory {path.parent}: {exc}"
            ) from exc

        try:
            weasyprint.HTML(string=document, base_url=str(STYLE_DIR)).write_pdf(
                str(path)
            )
        except Exception as exc:
            raise PDFRenderError(f"Failed to generate the PDF at {path}: {exc}") from exc

        self._validate_pdf_output(path)
        return path

    @staticmethod
    def _normalize_output_path(output_path: str | Path) -> Path:
        if isinstance(output_path, str):
            output_path = Path(output_path)
        if not isinstance(output_path, Path) or not output_path.name:
            raise InvalidOutputPathError(
                f"A valid output path for the report is required, got {output_path!r}"
            )
        if not output_path.suffix:
            output_path = output_path.with_suffix(".pdf")
        elif output_path.suffix.lower() != ".pdf":
            raise InvalidOutputPathError(
                f"The report must be saved as .pdf, got {output_path!r}"
            )
        return output_path

    @staticmethod
    def _validate_pdf_output(path: Path) -> None:
        try:
            if not path.exists() or path.stat().st_size == 0:
                raise InvalidPDFOutputError(
                    f"The generated report is missing or empty: {path}"
                )
            with path.open("rb") as fh:
                header = fh.read(4)
            if header != b"%PDF":
                raise InvalidPDFOutputError(
                    f"The generated document is not a valid PDF: {path}"
                )
            reader = PdfReader(str(path))
            if not reader.pages:
                raise InvalidPDFOutputError(
                    f"The generated document contains no pages: {path}"
                )
        except InvalidPDFOutputError:
            raise
        except Exception as exc:
            raise InvalidPDFOutputError(
                f"Failed to read the generated PDF: {exc}"
            ) from exc

    @classmethod
    def _build_pages(cls, analysis: CVAnalysis, job_search: JobSearchOutcome) -> dict:
        candidate = analysis.CANDIDATE_PROFILE
        report = analysis.RECRUITMENT_REPORT

        if not report.BEST_FIT_JOB_POSITIONS:
            raise MissingReportDataError(
                "The analysis must contain at least one target position "
                "(BEST_FIT_JOB_POSITIONS) to generate the report."
            )
        if job_search.summary is None:
            raise MissingReportDataError(
                "The search outcome must include a summary to generate the report."
            )

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