FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GOLDEN_DATASET_PATH=/app/data/golden/condition_briefings.jsonl \
    NEMO_GUARDRAILS_CONFIG=/app/guardrails

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-full.txt backend/requirements-hosted.txt ./
RUN pip install --no-cache-dir -r requirements-hosted.txt

COPY backend/app ./app
COPY data ./data
COPY infra/nemo ./guardrails

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
