"""Hybrid extraction routing and direct-format adapters."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pydantic import BaseModel

from doc_platform_contracts.extraction import ExtractedTextArtifact, ExtractionPage, ExtractionTrace

from extractor_service.config import ExtractorSettings, get_settings

PDF_TEXT_PATTERN = re.compile(rb"\(([^()]*)\)")
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SUPPORTED_MEDIA_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/json",
    "image/png",
    "image/jpeg",
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8"
PDF_SIGNATURE = b"%PDF-"


class ExtractionRequest(BaseModel):
    job_id: str
    document_id: str
    tenant_id: str
    source_media_type: str
    source_filename: str
    source_artifact_id: str
    inline_content_base64: str


@dataclass(slots=True)
class ExtractionResult:
    text: str
    extraction_path: str
    fallback_used: bool
    fallback_reason: str | None
    pages: list[ExtractionPage]


class ExtractionError(Exception):
    def __init__(self, *, error_code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def run_extraction(request: ExtractionRequest | dict, settings: ExtractorSettings | None = None) -> ExtractedTextArtifact:
    parsed_request = request if isinstance(request, ExtractionRequest) else ExtractionRequest.model_validate(request)
    settings = settings or get_settings()
    content = base64.b64decode(parsed_request.inline_content_base64)

    if parsed_request.source_media_type not in SUPPORTED_MEDIA_TYPES:
        raise ExtractionError(
            error_code="unsupported_media_type",
            message="Unsupported media type for extraction.",
        )

    if parsed_request.source_media_type == "application/pdf":
        validate_pdf_content(content)
        result = extract_pdf(content, parsed_request.source_artifact_id, settings)
    elif parsed_request.source_media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        result = extract_docx(content, parsed_request.source_artifact_id)
    elif parsed_request.source_media_type == "text/plain":
        result = extract_text(content, parsed_request.source_artifact_id)
    elif parsed_request.source_media_type == "application/json":
        result = extract_json(content, parsed_request.source_artifact_id)
    else:
        validate_image_content(content, parsed_request.source_media_type)
        result = build_ocr_placeholder(parsed_request.source_artifact_id)

    return ExtractedTextArtifact(
        job_id=parsed_request.job_id,
        document_id=parsed_request.document_id,
        tenant_id=parsed_request.tenant_id,
        source_media_type=parsed_request.source_media_type,
        extraction_path=result.extraction_path,
        fallback_used=result.fallback_used,
        fallback_reason=result.fallback_reason,
        page_count=len(result.pages),
        pages=result.pages,
        text=result.text,
        source_artifact_ids=[page.source_artifact_id for page in result.pages],
        produced_by=ExtractionTrace(
            provider="extractor-service",
            model="heuristic-router",
            version="0.1.0",
        ),
        created_at=datetime.now(UTC),
    )


def extract_pdf(content: bytes, source_artifact_id: str, settings: ExtractorSettings) -> ExtractionResult:
    matches = PDF_TEXT_PATTERN.findall(content)
    extracted = " ".join(
        match.decode("utf-8", errors="ignore").strip()
        for match in matches
        if match.decode("utf-8", errors="ignore").strip()
    ).strip()
    if len(extracted) >= settings.pdf_text_min_chars:
        return ExtractionResult(
            text=extracted,
            extraction_path="direct",
            fallback_used=False,
            fallback_reason=None,
            pages=[ExtractionPage(page_number=1, text=extracted, source_artifact_id=source_artifact_id)],
        )
    return ExtractionResult(
        text="",
        extraction_path="ocr",
        fallback_used=True,
        fallback_reason="embedded_text_unusable",
        pages=[ExtractionPage(page_number=1, text="", source_artifact_id=source_artifact_id)],
    )


def validate_pdf_content(content: bytes) -> None:
    if not content.startswith(PDF_SIGNATURE):
        raise ExtractionError(
            error_code="corrupt_pdf",
            message="PDF content is corrupt or unreadable.",
            status_code=422,
        )
    if b"/Encrypt" in content[:4096]:
        raise ExtractionError(
            error_code="encrypted_pdf",
            message="Encrypted PDFs are not supported.",
            status_code=422,
        )
    if b"%%EOF" not in content:
        raise ExtractionError(
            error_code="corrupt_pdf",
            message="PDF content is corrupt or unreadable.",
            status_code=422,
        )


def validate_image_content(content: bytes, media_type: str) -> None:
    if media_type == "image/png" and content.startswith(PNG_SIGNATURE):
        return
    if media_type == "image/jpeg" and content.startswith(JPEG_SIGNATURE):
        return
    raise ExtractionError(
        error_code="invalid_image_encoding",
        message="Image content is corrupt or has an invalid encoding.",
        status_code=422,
    )


def extract_docx(content: bytes, source_artifact_id: str) -> ExtractionResult:
    try:
        with ZipFile(BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise ExtractionError(
            error_code="invalid_input_payload",
            message="DOCX content is invalid or unreadable.",
            status_code=422,
        ) from exc
    root = ElementTree.fromstring(document_xml)
    text = "\n".join(
        node.text.strip()
        for node in root.findall(".//w:t", WORD_NAMESPACE)
        if node.text and node.text.strip()
    )
    return ExtractionResult(
        text=text,
        extraction_path="direct",
        fallback_used=False,
        fallback_reason=None,
        pages=[ExtractionPage(page_number=1, text=text, source_artifact_id=source_artifact_id)],
    )


def extract_text(content: bytes, source_artifact_id: str) -> ExtractionResult:
    text = content.decode("utf-8")
    return ExtractionResult(
        text=text,
        extraction_path="direct",
        fallback_used=False,
        fallback_reason=None,
        pages=[ExtractionPage(page_number=1, text=text, source_artifact_id=source_artifact_id)],
    )


def extract_json(content: bytes, source_artifact_id: str) -> ExtractionResult:
    parsed = json.loads(content.decode("utf-8"))
    text = json.dumps(parsed, indent=2, sort_keys=True)
    return ExtractionResult(
        text=text,
        extraction_path="direct",
        fallback_used=False,
        fallback_reason=None,
        pages=[ExtractionPage(page_number=1, text=text, source_artifact_id=source_artifact_id)],
    )


def build_ocr_placeholder(source_artifact_id: str) -> ExtractionResult:
    return ExtractionResult(
        text="",
        extraction_path="ocr",
        fallback_used=False,
        fallback_reason=None,
        pages=[ExtractionPage(page_number=1, text="", source_artifact_id=source_artifact_id)],
    )
