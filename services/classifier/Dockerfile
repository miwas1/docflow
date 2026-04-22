FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/contracts ./packages/contracts
COPY services/classifier ./services/classifier

ENV HF_HOME=/models/huggingface

RUN pip install --no-cache-dir \
    -e ./packages/contracts \
    -e ./services/classifier

EXPOSE 8002

CMD ["uvicorn", "classifier_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
