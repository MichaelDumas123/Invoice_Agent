# Ledgerly — AP invoice assistant prototype

A development-stage prototype for reviewing invoice details before recording them in an AP log. **This is not production-ready.** The current API uses synthetic demonstration values; it does not parse invoices, OCR documents, persist data durably, or write Excel workbooks. No invoice approval or payment capability is implemented.

## Safety and data

- Use synthetic files and data only. The demo store is in-memory and disappears on restart.
- Do not upload confidential or real vendor documents. The prototype may temporarily hold image preview bytes in memory.
- No external model/OCR provider is called. `PROVIDER_APPROVED` defaults to false. No provider key is needed or expected.
- Demo headers are not authentication and must never be exposed as a production login mechanism.
- Recording routes are development-only and create an in-memory demo record, not an Excel row or invoice approval.

## Requirements

- Python 3.12+ recommended (the backend package accepts Python 3.10+).
- Node.js 20+ and npm.
- Use separate backend and frontend terminals.

## Run backend

```bash
cd backend
uv sync --all-extras
uv run uvicorn invoice_assistant.api.main:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

Swagger UI: <http://127.0.0.1:8000/docs>. The API requires development identity headers for protected routes; see `backend/tests/test_demo_api.py` for a synthetic example. Mutations also require `X-CSRF-Token: local-demo-csrf-token`.

## Run frontend

```bash
cd frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>.

## Validate

```bash
cd backend
uv run pytest
uv run ruff check src tests
```

```bash
cd frontend
npm test
npm run build
npm run lint
```

## Planned next work

See `specs/001-invoice-intake/tasks.md`. The production design requires real authentication, durable workspace-scoped storage, sandboxed parsing/OCR, supported workbook compatibility, provider legal/privacy approval, and tested idempotent workbook publication before any real invoice data is processed.
