# AI Career Agent

Automatiza el análisis de curriculum vitae (LLM), la búsqueda de oportunidades
laborales en APIs externas y la generación de un informe PDF.

## Requisitos

- Docker + Docker Compose. No necesitas instalar Python ni dependencias en tu sistema.

## Arranque rápido (Docker)

```bash
# 1. Clona el repositorio
git clone <tu-repositorio> && cd ai-carrer-agent

# 2. Crea tu archivo de entorno y completa al menos OPENROUTER_KEY
cp .env.example .env

# 3. Levanta el servicio
docker compose up --build
```

- API y documentación interactiva (Swagger): http://localhost:8000/docs
- Los reportes PDF generados se persisten en el volumen `reports`.
- Claves opcionales: `ADZUNA_APP_ID`/`ADZUNA_API_KEY` y `OPEN_NINJA_API_KEY`
  (Remotive funciona sin credenciales).

> **Nota:** el estado de las tareas se guarda en memoria (1 worker de uvicorn),
> por lo que el servicio es de una sola instancia.

## Uso rápido con curl

```bash
curl -X POST http://localhost:8000/api/job_hunting \
  -F "file=@data-source/cv_ENG.md" \
  -F "location=Remote" \
  -F "max_positions=3"
```

La respuesta devuelve un `task_id`; consulta el estado con
`GET /api/tasks/{task_id}` y descarga el PDF con
`GET /api/tasks/{task_id}/report`.

## Desarrollo local (sin Docker)

```bash
python -m venv carreer-agent-env
carreer-agent-env/Scripts/activate   # Windows
pip install -r requirements.txt -r requirements-dev.txt
uvicorn main:app --app-dir src
```

Correr los tests:

```bash
pytest -q
```