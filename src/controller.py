from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.carrer_agent import CareerAgentService, TaskRecord, TaskStatus
from services.errors import TaskFailedError, TaskNotFoundError
from services.resume_extractor import get_extension

router = APIRouter()


def get_service(request: Request) -> CareerAgentService:
    service: CareerAgentService = request.app.state.career_service
    return service


class JobHuntingStarted(BaseModel):
    task_id: str
    status_url: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    status_url: str
    download_url: str | None = None


def _status_url(task_id: str) -> str:
    return f"/api/tasks/{task_id}"


def _download_url(task_id: str) -> str:
    return f"/api/tasks/{task_id}/report"


def _raise_failed(record: TaskRecord) -> None:
    raise TaskFailedError(
        status_code=record.error_status_code or 500,
        code=record.error_code or "internal_error",
        message=record.error_message or "El proceso falló internamente.",
    )


@router.post(
    "/job_hunting",
    status_code=202,
    response_model=JobHuntingStarted,
    summary="Inicia el pipeline análisis + búsqueda + reporte",
)
async def start_job_hunting(
    file: Annotated[UploadFile, File(description="Archivo del CV (.pdf, .txt, .md)")],
    location: Annotated[str | None, Form(description="Ubicación a filtrar en las búsquedas")] = None,
    max_positions: Annotated[int | None, Form(description="Tope de posiciones a buscar")] = None,
    service: CareerAgentService = Depends(get_service),
) -> JobHuntingStarted:
    content = await file.read()
    filename = file.filename or ""
    get_extension(filename)
    task_id = await service.start_pipeline(
        filename=filename,
        content=content,
        location=location,
        max_positions=max_positions,
    )
    return JobHuntingStarted(
        task_id=task_id,
        status_url=_status_url(task_id),
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    service: CareerAgentService = Depends(get_service),
) -> TaskStatusResponse:
    try:
        record = await service.get_task(task_id)
    except TaskNotFoundError:
        raise
    if record.status == TaskStatus.FAILED:
        _raise_failed(record)
    return TaskStatusResponse(
        task_id=task_id,
        status=record.status,
        status_url=_status_url(task_id),
        download_url=(
            _download_url(task_id)
            if record.status == TaskStatus.COMPLETED
            else None
        ),
    )


@router.get("/tasks/{task_id}/report")
async def download_report(
    task_id: str,
    service: CareerAgentService = Depends(get_service),
) -> FileResponse:
    try:
        record = await service.get_task(task_id)
    except TaskNotFoundError:
        raise
    if record.status == TaskStatus.FAILED:
        _raise_failed(record)
    if record.status != TaskStatus.COMPLETED or record.output_path is None:
        raise TaskFailedError(
            status_code=409,
            code="report_not_ready",
            message="El reporte aún no está disponible; la tarea sigue en ejecución.",
        )
    if not record.output_path.exists():
        raise TaskNotFoundError("El archivo del reporte no se encontró en el servidor.")
    return FileResponse(
        str(record.output_path),
        media_type="application/pdf",
        filename=record.output_path.name,
    )