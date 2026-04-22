# API Authentication Contract

Phase 2 authenticates external clients with static API keys.

## Contract

- External client requests are protected with static API keys.
- The request header name comes from `API_KEY_HEADER_NAME`.
- The default header is `X-API-Key`.
- Unknown or inactive keys must return `401 Unauthorized`.
- Phase 2 does not introduce JWT, OAuth, or token issuance flows.

## Example Request

```http
POST /v1/documents:upload HTTP/1.1
Host: api.example.test
X-API-Key: demo-secret-key
Idempotency-Key: 9f36b14e-7d68-4b35-9a8b-e8d3e672d8e1
Content-Type: multipart/form-data; boundary=----upload
```

Later phases may add key rotation or more advanced auth, but they should preserve the v1 protected-ingestion contract for existing external clients.
