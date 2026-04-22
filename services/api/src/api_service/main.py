"""FastAPI entrypoint for the API service."""

from pathlib import Path
from typing import Annotated

from api_service.auth import AuthenticatedClient
from api_service.config import APISettings
from api_service.dependencies import (
    _LoginRedirect,
    get_authenticated_client,
    get_authenticated_operator,
    get_db_session,
    get_enqueue_upload_dependency,
    get_internal_service_token,
    get_settings_dependency,
    get_storage_dependency,
)
from api_service.errors import APIError
from api_service.observability import setup_api_observability
from api_service.routers.dashboard.api_keys import router as dashboard_keys_router
from api_service.routers.dashboard.auth import router as dashboard_auth_router
from api_service.routers.dashboard.home import router as dashboard_home_router
from api_service.routers.dashboard.jobs import router as dashboard_jobs_router
from api_service.routers.dashboard.webhooks import router as dashboard_webhooks_router
from api_service.routers.landing import router as landing_router
from api_service.schemas import (
    AcceptedUploadResponse,
    JobResultsResponse,
    JobStatusResponse,
    OperatorDashboardSummaryResponse,
    OperatorJobDetailResponse,
    OperatorJobListItemResponse,
    WebhookDeliveryOutcomeRequest,
    WebhookDeliveryResponse,
    WebhookDispatchResponse,
)
from api_service.services.ingestion import EnqueueUploadJob, ingest_upload
from api_service.services.operator_dashboard import (
    get_operator_dashboard_summary,
    get_operator_job_detail,
    list_operator_jobs,
)
from api_service.services.results import get_job_results
from api_service.services.status import get_job_status
from api_service.services.webhooks import (
    get_webhook_dispatch_payload,
    record_webhook_delivery_outcome,
)
from api_service.storage import StorageAdapter
from fastapi import Depends, FastAPI, File, Header, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session


def create_app() -> FastAPI:
    app = FastAPI(title="Document Platform API", version="0.1.0")
    setup_api_observability(app)

    @app.exception_handler(APIError)
    async def handle_api_error(_, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(_LoginRedirect)
    async def handle_login_redirect(_, exc: _LoginRedirect) -> RedirectResponse:
        return RedirectResponse("/dashboard/login", status_code=302)

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "api"}

    @app.post(
        "/v1/documents:upload", status_code=202, response_model=AcceptedUploadResponse
    )
    def upload_document(
        file: UploadFile = File(...),
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        client: AuthenticatedClient = Depends(get_authenticated_client),
        session: Session = Depends(get_db_session),
        storage: StorageAdapter = Depends(get_storage_dependency),
        settings: APISettings = Depends(get_settings_dependency),
        enqueue_upload_job: EnqueueUploadJob = Depends(get_enqueue_upload_dependency),
    ) -> AcceptedUploadResponse:
        return ingest_upload(
            session=session,
            storage=storage,
            settings=settings,
            client=client,
            upload_file=file,
            idempotency_key=idempotency_key,
            enqueue_upload_job=enqueue_upload_job,
        )

    @app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
    def poll_job_status(
        job_id: str,
        client: AuthenticatedClient = Depends(get_authenticated_client),
        session: Session = Depends(get_db_session),
    ) -> JobStatusResponse:
        return get_job_status(session=session, client=client, job_id=job_id)

    @app.get("/v1/jobs/{job_id}/results", response_model=JobResultsResponse)
    def fetch_job_results(
        job_id: str,
        client: AuthenticatedClient = Depends(get_authenticated_client),
        session: Session = Depends(get_db_session),
    ) -> JobResultsResponse:
        return get_job_results(session=session, client=client, job_id=job_id)

    @app.get(
        "/internal/webhooks/jobs/{job_id}/dispatch",
        response_model=WebhookDispatchResponse,
    )
    def fetch_webhook_dispatch(
        job_id: str,
        request: Request,
        _: str = Depends(get_internal_service_token),
        session: Session = Depends(get_db_session),
    ) -> WebhookDispatchResponse:
        return get_webhook_dispatch_payload(
            session=session,
            job_id=job_id,
            base_results_url=str(request.base_url).rstrip("/"),
        )

    @app.post(
        "/internal/webhooks/jobs/{job_id}/deliveries/{delivery_id}",
        response_model=WebhookDeliveryResponse,
    )
    def persist_webhook_delivery_outcome(
        job_id: str,
        delivery_id: str,
        outcome: WebhookDeliveryOutcomeRequest,
        _: str = Depends(get_internal_service_token),
        session: Session = Depends(get_db_session),
    ) -> WebhookDeliveryResponse:
        return record_webhook_delivery_outcome(
            session=session,
            job_id=job_id,
            delivery_id=delivery_id,
            outcome=outcome,
        )

    @app.get("/internal/operator/jobs")
    def fetch_operator_jobs(
        status: str | None = None,
        client_id: str | None = None,
        q: str | None = None,
        limit: int = 50,
        _: str = Depends(get_authenticated_operator),
        session: Session = Depends(get_db_session),
    ) -> dict[
        str, OperatorDashboardSummaryResponse | list[OperatorJobListItemResponse]
    ]:
        return {
            "summary": get_operator_dashboard_summary(session=session),
            "jobs": list_operator_jobs(
                session=session,
                status=status,
                client_id=client_id,
                q=q,
                limit=limit,
            ),
        }

    @app.get(
        "/internal/operator/jobs/{job_id}", response_model=OperatorJobDetailResponse
    )
    def fetch_operator_job_detail(
        job_id: str,
        _: str = Depends(get_authenticated_operator),
        session: Session = Depends(get_db_session),
    ) -> OperatorJobDetailResponse:
        return get_operator_job_detail(session=session, job_id=job_id)

    @app.get("/internal/operator/dashboard", response_class=HTMLResponse)
    def render_operator_dashboard(
        _: str = Depends(get_authenticated_operator),
    ) -> HTMLResponse:
        template_path = (
            Path(__file__).resolve().parent / "templates" / "operator_dashboard.html"
        )
        return HTMLResponse(template_path.read_text(encoding="utf-8"))

    # Dashboard routers
    app.include_router(landing_router)
    app.include_router(dashboard_auth_router)
    app.include_router(dashboard_home_router)
    app.include_router(dashboard_keys_router)
    app.include_router(dashboard_webhooks_router)
    app.include_router(dashboard_jobs_router)

    return app


app = create_app()
