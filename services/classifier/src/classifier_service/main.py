"""FastAPI entrypoint for the classifier service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from classifier_service.inference import (
    ClassificationError,
    ClassificationRequest,
    run_classification,
    warm_runtime,
)
from classifier_service.observability import setup_classifier_observability


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        warm_runtime()
        yield

    app = FastAPI(title="Document Platform Classifier", version="0.1.0", lifespan=lifespan)
    setup_classifier_observability(app)

    @app.exception_handler(ClassificationError)
    async def handle_classification_error(_, exc: ClassificationError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"error_code": exc.error_code, "message": exc.message}},
        )

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "classifier"}

    @app.post("/v1/classifications:run")
    def classify_document(request: ClassificationRequest) -> dict:
        return run_classification(request).model_dump(mode="json")

    return app


app = create_app()
