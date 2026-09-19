FROM python:3.12-slim-bookworm

# WeasyPrint requiere librerías nativas de sistema (Pango, Cairo, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libffi8 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libjpeg62-turbo \
        libpixman-1-0 \
        shared-mime-info \
        fonts-dejavu-core \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    OUTPUT_DIR=/app/reports

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src ./src

EXPOSE 8000

STOPSIGNAL SIGTERM

# 1 worker: el estado de las tareas del pipeline vive en memoria
CMD ["uvicorn", "main:app", "--app-dir", "/app/src", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]