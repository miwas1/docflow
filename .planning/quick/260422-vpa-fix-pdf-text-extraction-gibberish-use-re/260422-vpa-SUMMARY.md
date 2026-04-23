# Quick Task Summary (260422-vpa)

## Goal

Fix gibberish `extracted_text` output for normal (digital) PDFs by replacing the byte-regex PDF "extraction" with a real PDF text parser, while keeping OCR fallback for scanned/unextractable PDFs.

## What Changed

- Updated extractor PDF direct extraction to use `pypdf` page text extraction instead of regex scanning raw PDF bytes (which could accidentally decode compressed stream junk).
- Added a small "usability" heuristic for extracted text; if it looks like noise, fall back to OCR.
- Made PDF-to-image conversion (`pdf2image`) a lazy import so non-OCR paths and unit tests can run in minimal dev environments.
- Updated extractor tests to generate a minimally valid one-page PDF (xref/trailer) to exercise the `pypdf` path.

## Verification

- `make test-extractor`

