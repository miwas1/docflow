"""Stage-based job polling service."""

from sqlalchemy.orm import Session

from api_service.auth import AuthenticatedClient
from api_service.errors import APIError
from api_service.repositories.jobs import get_job_for_client
from api_service.schemas import FailureResponse, JobStatusResponse


def get_job_status(
    *,
    session: Session,
    client: AuthenticatedClient,
    job_id: str,
) -> JobStatusResponse:
    job = get_job_for_client(session, client_id=client.client_id, job_id=job_id)
    if job is None:
        raise APIError(
            status_code=404,
            error_code="job_not_found",
            message="Job not found.",
        )

    failure = None
    if job.status == "failed" and job.failure_code and job.failure_message:
        failure = FailureResponse(code=job.failure_code, message=job.failure_message)

    return JobStatusResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        current_stage=job.current_stage,
        created_at=job.created_at,
        updated_at=job.updated_at,
        accepted_at=job.created_at,
        failure=failure,
    )
