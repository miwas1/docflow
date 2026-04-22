FROM python:3.13-slim

WORKDIR /app

# Install system deps required by psycopg (libpq) for any SQLAlchemy usage
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/contracts ./packages/contracts
COPY services/extractor ./services/extractor

RUN pip install --no-cache-dir \
    -e ./packages/contracts \
    -e ./services/extractor

EXPOSE 8001

CMD ["uvicorn", "extractor_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
