# External Ingestion API

## Upload Endpoint

`POST /v1/documents:upload`

### Authentication

- Send the static API key in the header defined by `API_KEY_HEADER_NAME`.
- The default header is `X-API-Key`.

### Headers

- `Idempotency-Key` — required for safe client retries

### Request

- Content type: `multipart/form-data`
- File field name: `file`

Supported file media types:

- `application/pdf`
- `image/png`
- `image/jpeg`
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `text/plain`
- `application/json`

Uploads are validated against the actual file content, not just the declared multipart media type.
Unsafe or malformed payloads fail before async processing begins.

Stable unsafe-input failure codes:

- `unsafe_input_type_mismatch`
- `encrypted_pdf`
- `invalid_input_payload`

### Accepted Response

```json
{
  "job_id": "9f6dbf44-c76f-4ce8-9c65-e5287b7dbda3",
  "document_id": "9802d760-e6c5-4d7d-b1c1-a70070b03bd2",
  "status": "queued",
  "current_stage": "accepted"
}
```

### Error Envelope

```json
{
  "error_code": "unsupported_media_type",
  "message": "Unsupported media type."
}
```

### Example Successful Request

```bash
curl -X POST http://localhost:8000/v1/documents:upload \
  -H "X-API-Key: demo-secret-key" \
  -H "Idempotency-Key: 9f36b14e-7d68-4b35-9a8b-e8d3e672d8e1" \
  -F "file=@sample.pdf;type=application/pdf"
```

### Example Unsupported Media Type

```json
{
  "error_code": "unsupported_media_type",
  "message": "Unsupported media type.",
  "details": {
    "content_type": "text/csv"
  }
}
```
