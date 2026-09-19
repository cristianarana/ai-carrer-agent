import logging
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from analyzer_agent.errors import (
    AnalysisError,
    AnalysisProviderError,
    AnalysisValidationError,
    EmptyResumeError,
    InvalidJSONError,
    ResumeTooLargeError,
)
from job_search_agent.errors import JobSearchError, NoMatchesError
from pdf_report.errors import ReportError
from services.errors import (
    FileReadError,
    FileTooLargeError,
    ServiceError,
    TaskFailedError,
    TaskNotFoundError,
    UnsupportedFileTypeError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ErrorInfo:
    status_code: int
    code: str


def error_info_for(exc: Exception) -> ErrorInfo:
    if isinstance(exc, TaskFailedError):
        return ErrorInfo(exc.status_code, exc.code)
    if isinstance(exc, TaskNotFoundError):
        return ErrorInfo(404, "task_not_found")
    if isinstance(
        exc,
        (
            UnsupportedFileTypeError,
            FileTooLargeError,
            FileReadError,
            EmptyResumeError,
            ResumeTooLargeError,
        ),
    ):
        return ErrorInfo(400, "invalid_resume")
    if isinstance(exc, NoMatchesError):
        return ErrorInfo(409, "no_matches")
    if isinstance(exc, (AnalysisValidationError, InvalidJSONError)):
        return ErrorInfo(422, "analysis_failed")
    if isinstance(exc, AnalysisProviderError):
        return ErrorInfo(422, "analysis_failed")
    if isinstance(exc, ReportError):
        return ErrorInfo(500, "report_failed")
    if isinstance(exc, AnalysisError):
        return ErrorInfo(400, "analysis_failed")
    if isinstance(exc, JobSearchError):
        return ErrorInfo(409, "job_search_failed")
    return ErrorInfo(500, "internal_error")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "request_validation",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(ServiceError)
    async def _handle_service_error(request: Request, exc: ServiceError):
        info = error_info_for(exc)
        return JSONResponse(
            status_code=info.status_code,
            content={"error": {"code": info.code, "message": str(exc)}},
        )

    @app.exception_handler(AnalysisError)
    async def _handle_analysis_error(request: Request, exc: AnalysisError):
        info = error_info_for(exc)
        return JSONResponse(
            status_code=info.status_code,
            content={"error": {"code": info.code, "message": str(exc)}},
        )

    @app.exception_handler(JobSearchError)
    async def _handle_job_search_error(request: Request, exc: JobSearchError):
        info = error_info_for(exc)
        return JSONResponse(
            status_code=info.status_code,
            content={"error": {"code": info.code, "message": str(exc)}},
        )

    @app.exception_handler(ReportError)
    async def _handle_report_error(request: Request, exc: ReportError):
        info = error_info_for(exc)
        return JSONResponse(
            status_code=info.status_code,
            content={"error": {"code": info.code, "message": str(exc)}},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception):
        if isinstance(exc, StarletteHTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"code": "http_error", "message": str(exc.detail)}},
            )
        logger.exception("Unhandled error in request %s", request.url.path)
        info = error_info_for(exc)
        return JSONResponse(
            status_code=info.status_code,
            content={"error": {"code": info.code, "message": str(exc) or info.code}},
        )