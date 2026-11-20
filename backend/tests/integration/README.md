# Synthetic integration smoke tests

Use the repository's synthetic fixtures only. From the project root:

```bash
cd backend
uv run pytest
uv run ruff check src tests
uv run mypy src
cd ../frontend
npm test
npm run build
npm run lint
npm run test:e2e
```

The integration tests verify accepted/rejected upload signatures, cross-workspace access denial, correction versioning, deterministic checks, workbook snapshot import/mapping/download, reviewer-only workbook recording, idempotent retries, and hard-stop no-write behavior in the in-memory prototype. These checks do not establish production durability, OIDC security, workbook fidelity for arbitrary customer files, malware scanning, or OCR accuracy.
