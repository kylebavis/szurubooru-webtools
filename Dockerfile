# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
# system deps (gallery-dl may need ffmpeg for some extractors; keep optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl ffmpeg git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml /app/
RUN pip install --upgrade pip && pip install -e .
COPY app /app/app
EXPOSE 8000
ENV UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
