import asyncio
import dataclasses
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.config import Settings, load_settings
from core.exceptions import error_info_for
from pipelines.job_hunter import JobHunterPipeline

from .errors import FileReadError, TaskNotFoundError
from .resume_extractor import check_size, extract_resume_text

logger = logging.getLogger(__name__)


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    status: str = TaskStatus.PENDING
    created_at: float = field(default_factory=time.monotonic)
    started_at: float | None = None
    finished_at: float | None = None
    output_path: Path | None = None
    error_status_code: int | None = None
    error_code: str | None = None
    error_message: str | None = None


PipelineFactory = Callable[..., JobHunterPipeline]


def default_pipeline_factory() -> JobHunterPipeline:
    return JobHunterPipeline(settings=load_settings())


class CareerAgentService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        pipeline_factory: PipelineFactory | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._pipeline_factory = pipeline_factory or default_pipeline_factory
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def start_pipeline(
        self,
        *,
        filename: str,
        content: bytes,
        location: str | None = None,
        max_positions: int | None = None,
    ) -> str:
        check_size(content, self._settings.max_cv_bytes)
        task_id = uuid.uuid4().hex
        record = TaskRecord(task_id=task_id)
        async with self._lock:
            self._tasks[task_id] = record
        asyncio.create_task(
            self._run(
                record,
                filename=filename,
                content=content,
                location=location,
                max_positions=max_positions,
            )
        )
        return task_id

    async def get_task(self, task_id: str) -> TaskRecord:
        async with self._lock:
            record = self._tasks.get(task_id)
        if record is None:
            raise TaskNotFoundError(f"Tarea no encontrada: {task_id}")
        return record

    async def _run(
        self,
        record: TaskRecord,
        *,
        filename: str,
        content: bytes,
        location: str | None,
        max_positions: int | None,
    ) -> None:
        running = dataclasses.replace(
            record,
            status=TaskStatus.RUNNING,
            started_at=time.monotonic(),
        )
        await self._store(running)
        logger.info("Task %s started", record.task_id)

        try:
            output_path = await asyncio.to_thread(
                self._execute,
                filename=filename,
                content=content,
                location=location,
                max_positions=max_positions,
                output_path=Path(self._settings.output_dir)
                / f"report_{record.task_id}.pdf",
            )
            finished_at = time.monotonic()
        except Exception as exc:
            info = error_info_for(exc)
            finished_at = time.monotonic()
            logger.exception(
                "Task %s failed [%s]: %s", record.task_id, info.code, exc
            )
            await self._store(
                dataclasses.replace(
                    running,
                    status=TaskStatus.FAILED,
                    finished_at=finished_at,
                    error_status_code=info.status_code,
                    error_code=info.code,
                    error_message=str(exc) or info.code,
                )
            )
            return

        await self._store(
            dataclasses.replace(
                running,
                status=TaskStatus.COMPLETED,
                finished_at=finished_at,
                output_path=Path(output_path),
            )
        )
        logger.info("Task %s completed path=%s", record.task_id, output_path)

    def _execute(
        self,
        *,
        filename: str,
        content: bytes,
        location: str | None,
        max_positions: int | None,
        output_path: Path,
    ) -> Path:
        resume_text = extract_resume_text(filename=filename, content=content)
        if not resume_text.strip():
            raise FileReadError("No se pudo extraer texto del archivo.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline = self._pipeline_factory()
        return pipeline.run(
            resume_text=resume_text,
            location=location,
            max_positions=max_positions,
            output_path=output_path,
        )

    async def _store(self, record: TaskRecord) -> None:
        async with self._lock:
            self._tasks[record.task_id] = record