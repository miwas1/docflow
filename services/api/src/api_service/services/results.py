"""Final results retrieval service."""

from sqlalchemy.orm import Session

from api_service.auth import AuthenticatedClient
from api_service.errors import APIError
from api_service.repositories.jobs import (
    get_classification_run_for_job,
    get_job_for_client,
    get_latest_artifact_for_job,
)
from api_service.schemas import (
    ArtifactReferenceResponse,
    ClassificationCandidateResponse,
    ClassificationMetadataResponse,
    JobResultsResponse,
)


def get_job_results(
    *,
    session: Session,
    client: AuthenticatedClient,
    job_id: str,
) -> JobResultsResponse:
    job = get_job_for_client(session, client_id=client.client_id, job_id=job_id)
    if job is None:
        raise APIError(
            status_code=404,
            error_code="job_not_found",
            message="Job not found.",
        )
    if job.status != "completed" or job.current_stage != "classified":
        raise APIError(
            status_code=409,
            error_code="results_not_ready",
            message="Results are not ready for this job.",
        )

    extracted_artifact = get_latest_artifact_for_job(session, job_id=job_id, artifact_type="extracted-text")
    classification_artifact = get_latest_artifact_for_job(session, job_id=job_id, artifact_type="classification-result")
    classification_run = get_classification_run_for_job(session, job_id=job_id)

    if extracted_artifact is None or classification_artifact is None or classification_run is None:
        raise APIError(
            status_code=409,
            error_code="results_not_ready",
            message="Results are not ready for this job.",
        )

    trace = classification_run.trace_json
    return JobResultsResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        extracted_text=extracted_artifact.metadata_json.get("text", ""),
        classification=ClassificationMetadataResponse(
            final_label=classification_run.final_label,
            confidence=classification_run.confidence,
            low_confidence_policy=classification_run.low_confidence_policy,
            threshold_applied=classification_run.threshold_applied,
            candidate_labels=[
                ClassificationCandidateResponse.model_validate(candidate)
                for candidate in classification_run.candidate_labels_json
            ],
            model=trace.get("model", ""),
            version=trace.get("version", ""),
        ),
        artifacts=[
            ArtifactReferenceResponse(
                artifact_type=artifact.artifact_type,
                stage=artifact.stage,
                storage_key=artifact.storage_key,
            )
            for artifact in (extracted_artifact, classification_artifact)
        ],
        completed_at=job.updated_at,
    )
