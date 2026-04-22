import base64
import io
import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import pytest
from extractor_service.extraction import (
    ExtractionError,
    ExtractionRequest,
    run_extraction,
)
from extractor_service.main import app
from PIL import Image as PILImage


def build_pdf_bytes(text: str) -> bytes:
    return f"%PDF-1.4\n1 0 obj\n<<>>\nstream\nBT ({text}) Tj ET\nendstream\nendobj\n%%EOF".encode()


def build_docx_bytes(text: str) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def build_request(*, media_type: str, filename: str, content: bytes) -> dict:
    return {
        "job_id": "job-123",
        "document_id": "doc-123",
        "tenant_id": "tenant-123",
        "source_media_type": media_type,
        "source_filename": filename,
        "source_artifact_id": "artifact-source-1",
        "inline_content_base64": base64.b64encode(content).decode(),
    }


def test_run_extraction_uses_direct_path_for_pdf_with_embedded_text() -> None:
    result = run_extraction(
        build_request(
            media_type="application/pdf",
            filename="sample.pdf",
            content=build_pdf_bytes("Invoice Number 42"),
        )
    )

    assert result.extraction_path == "direct"
    assert result.fallback_used is False
    assert result.text == "Invoice Number 42"


def test_run_extraction_falls_back_to_ocr_for_pdf_without_usable_text() -> None:
    mock_pil = PILImage.new("RGB", (10, 10))
    mock_ocr = MagicMock()
    mock_ocr.ocr.return_value = [[[None, ("Scanned invoice text", 0.97)]]]

    with (
        patch(
            "extractor_service.extraction.convert_from_bytes", return_value=[mock_pil]
        ),
        patch("extractor_service.extraction._get_ocr_engine", return_value=mock_ocr),
    ):
        result = run_extraction(
            build_request(
                media_type="application/pdf",
                filename="scan.pdf",
                content=b"%PDF-1.4\n%%EOF",
            )
        )

    assert result.extraction_path == "ocr"
    assert result.fallback_used is True
    assert result.fallback_reason == "embedded_text_unusable"
    assert result.text == "Scanned invoice text"


def test_run_extraction_normalizes_docx_txt_and_json_inputs() -> None:
    docx_result = run_extraction(
        build_request(
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="sample.docx",
            content=build_docx_bytes("Hello DOCX"),
        )
    )
    txt_result = run_extraction(
        build_request(
            media_type="text/plain",
            filename="sample.txt",
            content=b"Hello TXT",
        )
    )
    json_result = run_extraction(
        build_request(
            media_type="application/json",
            filename="sample.json",
            content=b'{"b": 2, "a": 1}',
        )
    )

    assert docx_result.text == "Hello DOCX"
    assert txt_result.text == "Hello TXT"
    assert json_result.text == json.dumps({"a": 1, "b": 2}, indent=2)
    assert [page.page_number for page in json_result.pages] == [1]


def test_extraction_endpoint_returns_normalized_payload() -> None:
    route = next(route for route in app.routes if route.path == "/v1/extractions:run")

    payload = route.endpoint(
        ExtractionRequest.model_validate(
            build_request(
                media_type="application/pdf",
                filename="sample.pdf",
                content=build_pdf_bytes("Payee Name"),
            )
        )
    )

    assert payload["extraction_path"] == "direct"
    assert payload["page_count"] == 1
    assert payload["source_artifact_ids"] == ["artifact-source-1"]


def test_run_extraction_uses_paddleocr_for_images() -> None:
    buf = io.BytesIO()
    PILImage.new("RGB", (32, 32)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    mock_ocr = MagicMock()
    mock_ocr.ocr.return_value = [[[None, ("Total Due 100", 0.98)]]]

    with patch("extractor_service.extraction._get_ocr_engine", return_value=mock_ocr):
        result = run_extraction(
            build_request(
                media_type="image/png",
                filename="scan.png",
                content=png_bytes,
            )
        )

    assert result.extraction_path == "ocr"
    assert result.fallback_used is False
    assert result.text == "Total Due 100"
    assert result.page_count == 1


def test_extraction_endpoint_rejects_unsupported_media_type() -> None:
    route = next(route for route in app.routes if route.path == "/v1/extractions:run")

    try:
        route.endpoint(
            ExtractionRequest.model_validate(
                build_request(
                    media_type="text/csv",
                    filename="sample.csv",
                    content=b"a,b,c",
                )
            )
        )
    except ExtractionError as exc:
        assert exc.error_code == "unsupported_media_type"
        assert exc.status_code == 400
    else:
        raise AssertionError("Expected ExtractionError for unsupported media type")


def test_run_extraction_rejects_encrypted_pdf() -> None:
    with pytest.raises(ExtractionError) as exc_info:
        run_extraction(
            build_request(
                media_type="application/pdf",
                filename="locked.pdf",
                content=b"%PDF-1.7\n1 0 obj\n<< /Encrypt 5 0 R >>\nendobj\n%%EOF",
            )
        )

    assert exc_info.value.error_code == "encrypted_pdf"
    assert exc_info.value.status_code == 422


def test_run_extraction_rejects_corrupt_pdf_instead_of_falling_back_to_ocr() -> None:
    with pytest.raises(ExtractionError) as exc_info:
        run_extraction(
            build_request(
                media_type="application/pdf",
                filename="broken.pdf",
                content=b"not-a-pdf",
            )
        )

    assert exc_info.value.error_code == "corrupt_pdf"
    assert exc_info.value.status_code == 422


def test_run_extraction_rejects_invalid_image_encoding() -> None:
    with pytest.raises(ExtractionError) as exc_info:
        run_extraction(
            build_request(
                media_type="image/png",
                filename="broken.png",
                content=b"not-a-real-image",
            )
        )

    assert exc_info.value.error_code == "invalid_image_encoding"
    assert exc_info.value.status_code == 422
