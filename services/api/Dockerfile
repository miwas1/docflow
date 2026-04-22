FROM python:3.12-slim

WORKDIR /app

# Install system deps required by psycopg (libpq) and other native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared contracts package then the service source
COPY packages/contracts ./packages/contracts
COPY services/api ./services/api
COPY services/orchestrator ./services/orchestrator

# Install packages in editable mode
RUN pip install --no-cache-dir \
    -e ./packages/contracts \
    -e ./services/api \
    -e ./services/orchestrator

COPY services/api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
