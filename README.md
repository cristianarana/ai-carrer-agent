# AI Career Agent

Automates the full job-hunting loop: LLM resume analysis, job search across
external job APIs, and a downloadable PDF report — all through a single API.

## Project overview

Upload a resume (`PDF`, `TXT`, or `MD`), and the service:

1. Extracts and validates the resume text.
2. Runs an LLM analysis (OpenRouter) that produces a structured recruitment
   report in English: best-fit job positions, ATS keywords, the
   "10-second recruiter test", a resume score, and a score improvement plan.
3. Searches real job postings on Remotive, Adzuna, and OpenNinja, scoring each
   posting against the analyzed profile.
4. Renders a PDF report with the analysis and the best matching jobs.

Work is executed as background tasks: `pending` → `running` → `completed`
(or `failed`), tracked in memory by `task_id`.

## Tech stack

| Layer        | Technology                                              |
| ------------ | ------------------------------------------------------- |
| Language     | Python 3.12                                             |
| API          | FastAPI + Uvicorn                                       |
| Validation   | Pydantic v2                                             |
| LLM          | OpenRouter API (default: `~deepseek/deepseek-flash-latest`) |
| Report (PDF) | WeasyPrint + Jinja2                                     |
| PDF parsing  | pypdf                                                   |
| Concurrency  | asyncio + worker threads                                |
| Deployment   | Docker / Docker Compose                                 |

## Quick start (Docker)

Requirements: Docker Engine (or Docker Desktop) with the daemon running.

```bash
# 1. Clone the repository, then create the environment file
cp .env.example .env

# 2. Set at least OPENROUTER_KEY in .env (required for the LLM analysis)
#    Optional keys: ADZUNA_APP_ID, ADZUNA_API_KEY, OPEN_NINJA_API_KEY
#    (Remotive works without credentials)

# 3. Build and start
docker compose up --build -d

# 4. Open the interactive API documentation
#    http://localhost:8000/docs
```

The service starts a single worker (task state lives in memory), so keep it as
a single instance.

## Run the image with Docker

Build and run the container manually:

```bash
# Build the image
docker build -t ai-carrer-agent .

# Run it (env vars from .env, PDFs persisted in a named volume)
docker run -d --name ai-carrer-agent \
  --env-file .env \
  -p 8000:8000 \
  -v reports:/app/reports \
  ai-carrer-agent
```

To publish it to a registry you own (optional):

```bash
docker tag ai-carrer-agent <your-user>/ai-carrer-agent:1.0
docker login
docker push <your-user>/ai-carrer-agent:1.0
docker pull <your-user>/ai-carrer-agent:1.0
```

Reported PDFs are written to `/app/reports` (`OUTPUT_DIR`), persisted in the
`reports` volume.

## API usage

### Start the pipeline

`POST /api/job_hunting` — multipart form:

| Field         | Type    | Required | Description                                  |
| ------------- | ------- | -------- | -------------------------------------------- |
| `file`        | file    | yes      | Resume (`.pdf`, `.txt`, `.md`, max 5 MB)     |
| `location`    | string  | no       | Location filter for the job search (e.g. `Remote`) |
| `max_positions` | int  | no       | Max positions to search for                  |

```bash
curl -X POST http://localhost:8000/api/job_hunting \
  -F "file=@path/to/resume.pdf" \
  -F "location=Remote" \
  -F "max_positions=3"
```

Response (`202 Accepted`):

```json
{
  "task_id": "3f2a9c1e...",
  "status_url": "/api/tasks/3f2a9c1e..."
}
```

### Check task status

`GET /api/tasks/{task_id}`

```bash
curl http://localhost:8000/api/tasks/3f2a9c1e...
```

Response:

```json
{
  "task_id": "3f2a9c1e...",
  "status": "completed",
  "status_url": "/api/tasks/3f2a9c1e...",
  "download_url": "/api/tasks/3f2a9c1e.../report"
}
```

### Download the report

`GET /api/tasks/{task_id}/report`

```bash
curl -o report.pdf http://localhost:8000/api/tasks/3f2a9c1e.../report
```

Returns the PDF (`application/pdf`) once the task is `completed`.

## Documentation

- Interactive Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Supported files and limits

- File types: `.pdf`, `.txt`, `.md` (text files must be UTF-8).
- Max upload size: `MAX_CV_BYTES` (default `5 MB`).
- Max resume text analyzed: `MAX_RESUME_CHARS` (default `60,000` chars).
- Scanned PDFs without a text layer cannot be extracted.

## Environment variables

| Variable                  | Default                        | Description                              |
| ------------------------- | ------------------------------ | ---------------------------------------- |
| `OPENROUTER_KEY`          | —                              | **Required.** LLM provider API key.      |
| `OPENROUTER_MODEL`        | `~deepseek/deepseek-flash-latest` | LLM model id for the analysis.        |
| `LOG_LEVEL`               | `INFO`                         | Logging level (`DEBUG`, `INFO`, ...).    |
| `SEARCH_MIN_MATCH`        | `0.85`                         | Minimum match score to accept a job.     |
| `SEARCH_TOP_N`            | `5`                            | Top positions considered per search.     |
| `SEARCH_MAX_WORKERS`      | `4`                            | Concurrent provider workers.             |
| `OUTPUT_DIR`              | `reports`                      | Directory for generated PDFs.            |
| `MAX_CV_BYTES`            | `5242880`                      | Max upload size in bytes.                |
| `MAX_RESUME_CHARS`        | `60000`                        | Max resume chars sent to the LLM.        |
| `ADZUNA_APP_ID`           | —                              | Adzuna app id (optional).                |
| `ADZUNA_API_KEY`          | —                              | Adzuna API key (optional).               |
| `OPEN_NINJA_API_KEY`      | —                              | OpenNinja API key (optional).            |

See `.env.example` for the full list of tunable parameters (retries, timeouts,
score weights, LLM token limits, etc.).

## Local development

```bash
python -m venv carreer-agent-env
# Windows:
carreer-agent-env/Scripts/activate
# macOS/Linux:
source carreer-agent-env/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --app-dir src
```

Run the tests:

```bash
pytest -q
```

## Notes

- Task state is kept in memory: run a single worker / single instance.
- PDF generation requires system libs for WeasyPrint; the provided Docker image
  already bundles them.
- All report content is generated in English.