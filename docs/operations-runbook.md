# Local prototype operations runbook

## Safety mode

- Run only with synthetic documents and test workbooks.
- `DEMO_AUTH_ENABLED=true` is a development-only header-based identity adapter, not real authentication.
- External OpenRouter/OCR extraction is disabled by default. Never enter provider secrets or real invoice data in this prototype.
- In-memory draft, audit, queue, mapping, and workbook state is lost on restart. Do not present the prototype as a production AP log.

## Start and validate

1. Start local PostgreSQL/object-store containers only if required for a development experiment; the current runtime adapters remain in-memory.
2. Start the backend from `backend/` using the command in the repository README.
3. Start the frontend from `frontend/` using the README command.
4. Run `uv run pytest`, `uv run ruff check src tests`, and `uv run mypy src` in `backend/`.
5. Run `npm test`, `npm run build`, `npm run lint`, and `npm run test:e2e` in `frontend/`.
6. Use the configured demo workspace and synthetic fixtures only. Confirm upload says unprocessed, validation is inconclusive for missing data, and only the explicit reviewer route can publish the in-memory workbook snapshot.

## Production blockers

Real authentication/OIDC, durable PostgreSQL repositories and migrations, production object storage/encryption, sandboxed conversion/OCR, provider legal/privacy approvals, durable queue, shared-lock/CAS recovery, rate limiting, secret scanning, backup/restore, monitoring, incident response, and representative AP/workbook approvals are not complete. Keep any live model/provider route disabled until each owner has approved the exact processing route and terms. No automatic fallback or model substitution is allowed.
