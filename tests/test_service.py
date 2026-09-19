import asyncio
from pathlib import Path

import pytest

from core.config import Settings
from job_search_agent.errors import NoMatchesError
from job_search_agent.interface.job_match import JobSearchSummary
from services.carrer_agent import CareerAgentService, TaskStatus
from services.errors import FileTooLargeError, TaskNotFoundError


def make_settings(tmp_path) -> Settings:
    return Settings(
        llm_model="fake-model",
        search_top_n=1,
        search_max_workers=1,
        max_resume_chars=1000,
        max_cv_bytes=1024,
        output_dir=str(tmp_path),
    )


class FakePipeline:
    def __init__(self, *, error=None, make_pdf: bool = True) -> None:
        self.error = error
        self.make_pdf = make_pdf
        self.last_resume_text: str | None = None

    def run(self, *, resume_text, location, max_positions, output_path):
        self.last_resume_text = resume_text
        if self.error:
            raise self.error
        if self.make_pdf:
            Path(output_path).write_bytes(b"%PDF-1.4\nfake")
        return Path(output_path)


async def _await_status(service, task_id, timeout=2.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        record = await service.get_task(task_id)
        if record.status != TaskStatus.PENDING:
            return record
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError("task did not leave pending state")
        await asyncio.sleep(0.005)


def test_service_completes_task(tmp_path):
    async def scenario() -> None:
        service = CareerAgentService(
            settings=make_settings(tmp_path),
            pipeline_factory=lambda: FakePipeline(),
        )
        task_id = await service.start_pipeline(
            filename="cv.md", content=b"# CV\nBackend engineer\n"
        )
        record = await _await_status(service, task_id)
        assert record.status == TaskStatus.COMPLETED
        assert record.error_code is None
        assert record.output_path is not None
        assert record.output_path.exists()
        assert record.finished_at is not None

    asyncio.run(scenario())


def test_service_marks_no_matches_failure(tmp_path):
    async def scenario() -> None:
        error = NoMatchesError(
            JobSearchSummary(), reason="none_above_threshold"
        )
        service = CareerAgentService(
            settings=make_settings(tmp_path),
            pipeline_factory=lambda: FakePipeline(error=error),
        )
        task_id = await service.start_pipeline(
            filename="cv.txt", content=b"CV text"
        )
        record = await _await_status(service, task_id)
        assert record.status == TaskStatus.FAILED
        assert record.error_code == "no_matches"
        assert record.error_status_code == 409
        assert "none_above_threshold" in record.error_message

    asyncio.run(scenario())


def test_service_rejects_oversized_file(tmp_path):
    async def scenario() -> None:
        service = CareerAgentService(settings=make_settings(tmp_path))
        with pytest.raises(FileTooLargeError):
            await service.start_pipeline(
                filename="cv.txt", content=b"x" * (1024 + 1)
            )

    asyncio.run(scenario())


def test_service_marks_invalid_extension_failure(tmp_path):
    async def scenario() -> None:
        service = CareerAgentService(
            settings=make_settings(tmp_path),
            pipeline_factory=lambda: FakePipeline(),
        )
        task_id = await service.start_pipeline(
            filename="cv.exe", content=b"MZ..."
        )
        record = await _await_status(service, task_id)
        assert record.status == TaskStatus.FAILED
        assert record.error_code == "invalid_resume"
        assert record.error_status_code == 400
        assert ".exe" in record.error_message

    asyncio.run(scenario())


def test_service_unknown_task_raises(tmp_path):
    async def scenario() -> None:
        service = CareerAgentService(settings=make_settings(tmp_path))
        with pytest.raises(TaskNotFoundError):
            await service.get_task("missing")

    asyncio.run(scenario())