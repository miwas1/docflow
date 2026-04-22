FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/contracts ./packages/contracts
COPY services/orchestrator ./services/orchestrator

RUN pip install --no-cache-dir \
    -e ./packages/contracts \
    -e ./services/orchestrator

CMD ["celery", "-A", "orchestrator_service.celery_app:celery_app", "worker", \
     "--loglevel=INFO", "--without-gossip", "--without-mingle"]
