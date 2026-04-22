FROM python:3.13-slim

WORKDIR /app

# System deps:
#   libpq-dev / gcc     — psycopg (SQLAlchemy)
#   poppler-utils       — pdf2image PDF-to-image conversion
#   libglib2.0-0 libsm6 libxrender1 libxext6 libgomp1 — OpenCV / PaddleOCR runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY packages/contracts ./packages/contracts
COPY services/extractor ./services/extractor

RUN pip install --no-cache-dir \
    -e ./packages/contracts \
    -e ./services/extractor

EXPOSE 8001

CMD ["uvicorn", "extractor_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
