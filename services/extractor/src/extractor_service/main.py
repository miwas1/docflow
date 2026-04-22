"""FastAPI entrypoint for the extractor service."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from extractor_service.extraction import ExtractionError, ExtractionRequest, run_extraction
from extractor_service.observability import setup_extractor_observability


def create_app() -> FastAPI:
    app = FastAPI(title="Document Platform Extractor", version="0.1.0")
    setup_extractor_observability(app)

    @app.exception_handler(ExtractionError)
    async def handle_extraction_error(_, exc: ExtractionError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"error_code": exc.error_code, "message": exc.message}},
        )

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "extractor"}

    @app.post("/v1/extractions:run")
    def extract_document(request: ExtractionRequest) -> dict:
        return run_extraction(request).model_dump(mode="json")

    return app


app = create_app()
