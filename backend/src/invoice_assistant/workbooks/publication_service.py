"""Safe logical publication service for the local process only.

The in-memory adapter is useful for development tests. Production needs a shared
transactional database and object store implementing the same compare-and-swap.
"""

from dataclasses import dataclass
from hashlib import sha256
from threading import RLock
from typing import Any

from invoice_assistant.domain.audit import make_audit_event
from invoice_assistant.domain.validation import check_duplicates
from invoice_assistant.persistence.object_store import MemoryObjectStore
from invoice_assistant.workbooks.record_intent_service import IntentConflict, intents
from invoice_assistant.workbooks.version_store import VersionConflict, WorkbookVersionStore


@dataclass(frozen=True)
class PublicationResult:
    status: str
    reference: str
    version: int
    audit_event: dict[str, Any]


class PublicationService:
    def __init__(self) -> None:
        self.versions = WorkbookVersionStore(MemoryObjectStore())
        self._lock = RLock()
        self._idempotency: dict[tuple[str, str], tuple[str, PublicationResult]] = {}
        self._records: dict[str, list[dict[str, Any]]] = {}
        self._workbook_locks: dict[tuple[str, str], RLock] = {}
        self._workspace_duplicate_locks: dict[str, RLock] = {}

    async def publish(self, *, workspace_id: str, actor_id: str, workbook_id: str, expected_version: int, idempotency_key: str, payload: bytes, invoice: dict[str, Any], existing_records: list[dict[str, Any]], warning_acknowledgements: list[dict[str, str]]) -> PublicationResult:
        if not idempotency_key or len(idempotency_key) < 16:
            raise ValueError("A stable idempotency key of at least 16 characters is required")
        fingerprint = sha256(payload + repr(sorted(invoice.items())).encode()).hexdigest()
        with self._lock:
            workbook_lock = self._workbook_locks.setdefault((workspace_id, workbook_id), RLock())
            duplicate_lock = self._workspace_duplicate_locks.setdefault(workspace_id, RLock())
        with duplicate_lock, workbook_lock, self._lock:
            try:
                intent_fingerprint = sha256(payload + repr(sorted(invoice.items())).encode() + str(expected_version).encode()).digest()
                intent = intents.begin(workspace_id, idempotency_key, intent_fingerprint, {"workbook_id": workbook_id, "expected_version": expected_version})
            except IntentConflict as exc:
                raise VersionConflict(str(exc)) from exc
            if intent["status"] == "committed" and "result" in intent:
                saved = intent["result"]
                return PublicationResult(saved["status"], saved["reference"], saved["version"], saved["audit_event"])
            if intent.get("status") == "pending" and intent.get("fingerprint"):
                intent["status"] = "staging"
            prior = self._idempotency.get((workspace_id, idempotency_key))
            if prior:
                if prior[0] != fingerprint:
                    raise VersionConflict("Idempotency key was reused with a different payload")
                return prior[1]
            comparable = {
                "vendor_name": {"value": invoice.get("vendor_name")},
                "invoice_number": {"value": invoice.get("invoice_number")},
            }
            candidate_duplicates = check_duplicates(comparable, [*existing_records, *self._records.get(workspace_id, [])])
            if candidate_duplicates.status.value == "warning":
                acknowledgements = {item.get("warning_id"): item.get("reason", "").strip() for item in warning_acknowledgements}
                if not acknowledgements.get("duplicate") and not acknowledgements.get("duplicate_candidate"):
                    raise PermissionError("Duplicate candidate requires reviewer acknowledgement and reason")
            if any(not item.get("reason", "").strip() for item in warning_acknowledgements):
                raise PermissionError("Every warning acknowledgement requires a reason")
            current_version = self.versions.current_version(workspace_id, workbook_id)
            if current_version != expected_version:
                raise VersionConflict("Workbook version changed; reload, revalidate, and request reviewer confirmation again")
            candidate = await self.versions.stage(workspace_id, workbook_id, expected_version, payload)
            try:
                self.versions.publish(candidate, expected_version)
            except VersionConflict:
                raise
            reference = f"{workbook_id}:{candidate.version}"
            event = make_audit_event(workspace_id, actor_id, "record_log_entry", reference, {"warning_acknowledgements": warning_acknowledgements, "invoice_number": invoice.get("invoice_number")})
            result = PublicationResult("recorded", reference, candidate.version, event)
            self._idempotency[(workspace_id, idempotency_key)] = (fingerprint, result)
            records = self._records.setdefault(workspace_id, [])
            if not any(item.get("reference") == reference for item in records):
                records.append({**invoice, "reference": reference})
            intents.finish(workspace_id, idempotency_key, {"status": result.status, "reference": result.reference, "version": result.version, "audit_event": result.audit_event})
            return result


publication_service = PublicationService()
