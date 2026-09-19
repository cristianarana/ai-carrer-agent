import time
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient

from core.config import Settings
from job_search_agent.errors import NoMatchesError
from job_search_agent.interface.job_match import JobSearchSummary
from main import create_app
from services.carrer_agent import CareerAgentService


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
    def __init__(self, *, error=None) -> None:
        self.error = error

    def run(self, *, resume_text, location, max_positions, output_path):
        if self.error:
            raise self.error
        Path(output_path).write_bytes(b"%PDF-1.4\nfake report")
        return Path(output_path)


@contextmanager
def client_for(tmp_path, *, error=None):
    service = CareerAgentService(
        settings=make_settings(tmp_path),
        pipeline_factory=lambda: FakePipeline(error=error),
    )
    with TestClient(create_app(career_service=service)) as client:
        yield client


def _wait_for(client: TestClient, task_id: str, *, status_code: int | None = None):
    for _ in range(100):
        resp = client.get(f"/api/tasks/{task_id}")
        if status_code is not None and resp.status_code == status_code:
            return resp
        if status_code is None and resp.status_code == 200 and resp.json()["status"] == "completed":
            return resp
        time.sleep(0.01)
    raise AssertionError(f"task did not reach expected state (status_code={status_code})")


def test_job_hunting_full_flow(tmp_path):
    with client_for(tmp_path) as client:
        resp = client.post(
            "/api/job_hunting",
            files={"file": ("cv.md", b"# CV\nBackend Engineer\n", "text/markdown")},
        )
        assert resp.status_code == 202
        body = resp.json()
        task_id = body["task_id"]
        assert body["status_url"] == f"/api/tasks/{task_id}"

        status = _wait_for(client, task_id)
        data = status.json()
        assert data["status"] == "completed"
        assert data["download_url"] == f"/api/tasks/{task_id}/report"

        down = client.get(data["download_url"])
        assert down.status_code == 200
        assert down.content.startswith(b"%PDF")
        assert down.headers["content-type"] == "application/pdf"


def test_job_hunting_accepts_pdf_file(tmp_path):
    with client_for(tmp_path) as client:
        resp = client.post(
            "/api/job_hunting",
            files={"file": ("cv.pdf", b"%PDF-1.4\n% fake", "application/pdf")},
        )
        assert resp.status_code == 202


def test_job_hunting_rejects_invalid_extension(tmp_path):
    with client_for(tmp_path) as client:
        resp = client.post(
            "/api/job_hunting",
            files={"file": ("cv.exe", b"MZ", "application/x-msdownload")},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "invalid_resume"
        assert ".exe" in body["error"]["message"]


def test_job_hunting_rejects_oversized_file(tmp_path):
    with client_for(tmp_path) as client:
        resp = client.post(
            "/api/job_hunting",
            files={"file": ("cv.md", b"x" * (1024 + 1), "text/markdown")},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_resume"


def test_report_not_ready_while_running(tmp_path):
    class SlowPipeline:
        def run(self, *, resume_text, location, max_positions, output_path):
            time.sleep(0.3)
            Path(output_path).write_bytes(b"%PDF-1.4\nfake report")
            return Path(output_path)

    service = CareerAgentService(
        settings=make_settings(tmp_path),
        pipeline_factory=lambda: SlowPipeline(),
    )
    with TestClient(create_app(career_service=service)) as client:
        resp = client.post(
            "/api/job_hunting",
            files={"file": ("cv.md", b"# CV\nBackend\n", "text/markdown")},
        )
        task_id = resp.json()["task_id"]
        resp = client.get(f"/api/tasks/{task_id}/report")
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "report_not_ready"


def test_task_not_found_returns_404(tmp_path):
    with client_for(tmp_path) as client:
        resp = client.get("/api/tasks/missing")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "task_not_found"


def test_no_matches_returns_conflict(tmp_path):
    error = NoMatchesError(JobSearchSummary(), reason="none_above_threshold")
    with client_for(tmp_path, error=error) as client:
        resp = client.post(
            "/api/job_hunting",
            files={"file": ("cv.md", b"# CV\nBackend\n", "text/markdown")},
        )
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]

        conflict = _wait_for(client, task_id, status_code=409)
        body = conflict.json()
        assert body["error"]["code"] == "no_matches"
        assert "none_above_threshold" in body["error"]["message"]