"""Development-only API routes for a synthetic invoice-review MVP."""

from __future__ import annotations

import secrets
import threading
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from invoice_assistant.api.csrf import validate_csrf
from invoice_assistant.api.schemas import (
    ChatRequest,
    ChatResponse,
    CorrectionRequest,
    DocumentResponse,
    MappingRequest,
    PolicyUpdateRequest,
    RecordIntent,
    RecordRequest,
    RecordResult,
    Role,
    ValidationRun,
)
from invoice_assistant.auth.authorization import CurrentPrincipal, Principal, require_role
from invoice_assistant.config import settings
from invoice_assistant.documents.conversion import convert_document, page_summaries
from invoice_assistant.documents.intake import validate_document
from invoice_assistant.domain.audit_service import record_event
from invoice_assistant.domain.demo_service import create_demo_draft
from invoice_assistant.domain.policy import WorkspacePolicy, validate_policy_update
from invoice_assistant.domain.store import store
from invoice_assistant.domain.validation import validate_invoice
from invoice_assistant.workbooks.publication_service import VersionConflict, publication_service
from invoice_assistant.workbooks.record_intent_service import intents
from invoice_assistant.workbooks.service import (
    append_invoice,
    create_new_workbook,
    get_workbook,
    read_invoice_records,
    save_mapping,
    update_published_workbook,
    upload_workbook,
)

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}")
_record_lock = threading.RLock()
FIELD_NAMES = {"vendor_name", "invoice_number", "invoice_date", "due_date", "po_number", "currency", "subtotal", "tax", "charges", "discount", "total"}


def verify_workspace(workspace_id: str, principal: Principal) -> None:
    if principal.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Resource not found")


@router.post("/documents", status_code=202)
async def upload_document(
    workspace_id: str,
    request: Request,
    principal: CurrentPrincipal,
    file: Annotated[UploadFile, File()],
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> dict:
    validate_csrf(request, x_csrf_token)
    verify_workspace(workspace_id, principal)
    if settings.environment != "development":
        raise HTTPException(status_code=503, detail="Production document storage and isolated processing are not configured")
    content = await file.read(settings.max_upload_bytes + 1)
    await file.close()
    try:
        checked = validate_document(file.filename or "invoice", file.content_type or "", content, settings.max_upload_bytes)
    except OverflowError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except TypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    object_key = f"{workspace_id}/documents/{secrets.token_hex(16)}/{checked.filename}"
    from invoice_assistant.persistence.object_store import object_store
    stored = await object_store.put_private(workspace_id, object_key, checked.content, checked.detected_type)
    draft = create_demo_draft(workspace_id, checked.filename, checked.detected_type, checked.content)
    draft["object_key"] = object_key
    try:
        rendered_pages = convert_document(checked)
        draft["pages"] = page_summaries(rendered_pages)
        draft["preview_pages"] = rendered_pages
        draft["warnings"] = ["Pages were rendered, but OCR and invoice extraction are not implemented; fields remain missing and validation is inconclusive."]
        status = "rendered_not_extracted"
    except (ValueError, RuntimeError) as exc:
        draft["pages"] = [{"page": 1, "status": "failed", "preview_url": None, "error": str(exc)}]
        draft["warnings"] = ["Document conversion failed; invoice was not extracted."]
        status = "conversion_failed"
    store.workspace(workspace_id).documents[draft["document_id"]] = {"id": draft["document_id"], "object_key": object_key, "checksum": stored.etag, "byte_size": stored.size, "name": checked.filename, "detected_type": checked.detected_type, "status": status}
    draft["audit"].append({"event": "uploaded", "at": datetime.now(timezone.utc).isoformat(), "actor": principal.user_id, "detail": "File validated; extraction is unavailable in this demo."})
    notice = "Pages rendered; OCR and extraction are disabled. Review and enter invoice values manually." if status == "rendered_not_extracted" else "Document conversion failed. No invoice values were extracted."
    return {"document_id": draft["document_id"], "draft_id": draft["id"], "status": status, "pages": draft["pages"], "notice": notice}


@router.get("/drafts")
def list_drafts(workspace_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    state = store.workspace(workspace_id)
    return {
        "items": list(state.drafts.values()),
        "page": 1,
        "page_size": max(1, len(state.drafts)),
        "total": len(state.drafts),
    }


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(workspace_id: str, document_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    metadata = store.workspace(workspace_id).documents.get(document_id)
    matches = [draft for draft in store.workspace(workspace_id).drafts.values() if draft["document_id"] == document_id]
    if not matches or metadata is None:
        raise HTTPException(status_code=404, detail="Document not found")
    draft = matches[0]
    message = "OCR and invoice extraction are not enabled in this prototype." if metadata["status"] == "rendered_not_extracted" else "Document conversion did not complete."
    return {"id": document_id, "status": metadata["status"], "detected_type": metadata["detected_type"], "byte_size": metadata["byte_size"], "checksum": metadata["checksum"], "page_count": len(draft["pages"]), "pages": draft["pages"], "error": message}


@router.get("/documents/{document_id}/pages/{page}/preview")
async def get_document_preview(workspace_id: str, document_id: str, page: int, principal: CurrentPrincipal) -> Response:
    verify_workspace(workspace_id, principal)
    matches = [draft for draft in store.workspace(workspace_id).drafts.values() if draft["document_id"] == document_id]
    if not matches or page < 1 or page > len(matches[0]["pages"]):
        raise HTTPException(status_code=404, detail="Document page not found")
    try:
        from invoice_assistant.persistence.object_store import object_store
        await object_store.get_private(workspace_id, store.workspace(workspace_id).documents[document_id]["object_key"])
    except (FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail="Document page not found") from exc
    page_data = matches[0]["pages"][page - 1]
    rendered_pages = matches[0].get("preview_pages", [])
    if page > len(rendered_pages) or rendered_pages[page - 1].image_png is None:
        raise HTTPException(status_code=404, detail=page_data.get("error", "Preview is unavailable"))
    return Response(content=rendered_pages[page - 1].image_png, media_type="image/png", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/drafts/{draft_id}")
def get_draft(workspace_id: str, draft_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    draft = store.get_draft(workspace_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/drafts/{draft_id}")
async def correct_field(workspace_id: str, draft_id: str, payload: CorrectionRequest, request: Request, principal: CurrentPrincipal, x_csrf_token: Annotated[str | None, Header()] = None) -> dict:
    validate_csrf(request, x_csrf_token)
    verify_workspace(workspace_id, principal)
    if principal.role not in {Role.OPERATOR, Role.REVIEWER}:
        raise HTTPException(status_code=403, detail="Operator or reviewer role required")
    draft = store.get_draft(workspace_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if payload.expected_version != draft["version"]:
        raise HTTPException(status_code=409, detail="Draft changed; reload before editing")
    if payload.field_name not in FIELD_NAMES:
        raise HTTPException(status_code=422, detail="Unknown invoice field")
    if payload.field_name in {"invoice_date", "due_date"} and payload.value:
        from datetime import date
        try:
            date.fromisoformat(payload.value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invoice dates must use ISO format YYYY-MM-DD") from exc
    if payload.field_name == "currency" and payload.value and (len(payload.value) != 3 or not payload.value.isalpha()):
        raise HTTPException(status_code=422, detail="Currency must be a three-letter ISO code")
    if payload.field_name in {"vendor_name", "invoice_number", "po_number"} and "\x00" in payload.value:
        raise HTTPException(status_code=422, detail="Text fields cannot contain NUL characters")
    if payload.field_name in {"subtotal", "tax", "charges", "discount", "total"} and payload.value:
        from decimal import Decimal, InvalidOperation
        try:
            amount = Decimal(payload.value)
        except InvalidOperation as exc:
            raise HTTPException(status_code=422, detail="Monetary values must be decimal numbers") from exc
        if not amount.is_finite():
            raise HTTPException(status_code=422, detail="Monetary values must be finite")
    if payload.field_name == "currency" and payload.value:
        payload.value = payload.value.upper()
    field = draft["fields"][payload.field_name]
    field.update({"value": payload.value, "state": "present", "uncertainty": "Entered or corrected by a human; verify against source.", "origin": "user"})
    draft["version"] += 1
    draft["status"] = "needs_review"
    draft["warnings"] = [w for w in draft["warnings"] if not (payload.field_name == "po_number" and "PO number is missing" in w)]
    draft["audit"].append({"event": "field_corrected", "at": datetime.now(timezone.utc).isoformat(), "actor": principal.user_id, "detail": f"{payload.field_name} corrected", "field": payload.field_name})
    await record_event(workspace_id, principal.user_id, "field_corrected", draft_id, {"field": payload.field_name})
    return draft


@router.post("/drafts/{draft_id}/messages", response_model=ChatResponse)
def chat(workspace_id: str, draft_id: str, payload: ChatRequest, request: Request, principal: CurrentPrincipal, x_csrf_token: Annotated[str | None, Header()] = None) -> ChatResponse:
    validate_csrf(request, x_csrf_token)
    verify_workspace(workspace_id, principal)
    draft = store.get_draft(workspace_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    conversation = store.workspace(workspace_id).conversations.setdefault(draft_id, [])
    now = datetime.now(timezone.utc).isoformat()
    conversation.append({"role": "user", "actor": principal.user_id, "text": payload.message, "at": now})
    answer = "This local MVP uses synthetic invoice values only. I can’t verify invoice contents yet. Please compare every field with the source and edit the draft as needed."
    conversation.append({"role": "assistant", "actor": "system", "text": answer, "at": datetime.now(timezone.utc).isoformat(), "provenance": "deterministic_demo"})
    return ChatResponse(message=answer)


@router.get("/drafts/{draft_id}/messages")
def get_messages(workspace_id: str, draft_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    if store.get_draft(workspace_id, draft_id) is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"items": store.workspace(workspace_id).conversations.get(draft_id, [])}


@router.post("/drafts/{draft_id}/validate", response_model=ValidationRun)
def validate_draft(workspace_id: str, draft_id: str, principal: CurrentPrincipal, workbook_id: str | None = None) -> ValidationRun:
    verify_workspace(workspace_id, principal)
    draft = store.get_draft(workspace_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if workbook_id:
        if workbook_id not in store.workspace(workspace_id).workbooks:
            raise HTTPException(status_code=404, detail="Workbook not found")
        if draft.get("target_workbook_id") != workbook_id:
            draft["version"] += 1
            draft["status"] = "needs_review"
            draft["validation_stale"] = True
        draft["target_workbook_id"] = workbook_id
    else:
        workbook_id = draft.get("target_workbook_id")
    selected_records = read_invoice_records(workspace_id, workbook_id) if workbook_id else []
    raw = validate_invoice(draft["fields"], WorkspacePolicy(), list(store.workspace(workspace_id).records.values()), selected_records)
    draft["validation_stale"] = False
    run = ValidationRun(id=f"validation_{secrets.token_hex(8)}", draft_id=draft_id, draft_version=draft["version"], policy_version=1, results=raw)
    run_data = run.model_dump(mode="json")
    mapping = store.workspace(workspace_id).mappings.get(workbook_id or "")
    run_data["mapping_version"] = mapping.get("version", 0) if mapping else 0
    run_data["workbook_id"] = workbook_id
    run_data["workbook_version"] = store.workspace(workspace_id).workbooks.get(workbook_id or "", {}).get("version", 0)
    store.workspace(workspace_id).validation_runs[run.id] = run_data
    return run


@router.post("/workbooks", status_code=201)
async def add_workbook(
    workspace_id: str,
    request: Request,
    principal: CurrentPrincipal,
    file: Annotated[UploadFile | None, File()] = None,
    name: str = "Invoice Log",
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> dict:
    validate_csrf(request, x_csrf_token)
    verify_workspace(workspace_id, principal)
    if settings.environment != "development":
        raise HTTPException(status_code=503, detail="Production workbook storage and validation are not configured")
    try:
        if file is None:
            return create_new_workbook(workspace_id, name)
        content = await file.read(50 * 1024 * 1024 + 1)
        await file.close()
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Workbook exceeds upload limit")
        if not content.startswith(b"PK"):
            raise HTTPException(status_code=415, detail="Workbook content is not a valid XLSX package")
        item = upload_workbook(workspace_id, file.filename or "Invoice Log.xlsx", content)
        await record_event(workspace_id, principal.user_id, "workbook_imported", str(item["id"]), {"name": item["name"], "workbook_id": item["id"]})
        return item
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/workbooks/{workbook_id}")
def read_workbook(workspace_id: str, workbook_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    item = get_workbook(workspace_id, workbook_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Workbook not found")
    return item


@router.post("/workbooks/{workbook_id}/mappings")
def map_workbook(
    workspace_id: str,
    workbook_id: str,
    payload: MappingRequest,
    request: Request,
    principal: CurrentPrincipal,
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> dict:
    validate_csrf(request, x_csrf_token)
    verify_workspace(workspace_id, principal)
    try:
        mapping_state = store.workspace(workspace_id).mappings.get(workbook_id)
        current_mapping_version = mapping_state.get("version", 0) if mapping_state else 0
        expected_version = payload.expected_version
        if expected_version != current_mapping_version:
            raise HTTPException(status_code=409, detail="Mapping version changed; reload before updating")
        if any(field not in FIELD_NAMES for field in payload.field_to_column):
            raise HTTPException(status_code=422, detail="Mapping includes unsupported invoice fields")
        result = save_mapping(workspace_id, workbook_id, payload.worksheet, payload.field_to_column, payload.required_fields, expected_version)
        for draft in store.workspace(workspace_id).drafts.values():
            if draft.get("target_workbook_id") == workbook_id:
                draft["version"] += 1
                draft["status"] = "needs_review"
                draft["validation_stale"] = True
                draft["audit"].append({"event": "mapping_changed", "at": datetime.now(timezone.utc).isoformat(), "actor": principal.user_id, "detail": "Workbook mapping changed; review is required again."})
        return result
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/workbooks/{workbook_id}/download")
def download_workbook(workspace_id: str, workbook_id: str, principal: CurrentPrincipal) -> Response:
    verify_workspace(workspace_id, principal)
    item = store.workspace(workspace_id).workbooks.get(workbook_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Workbook not found")
    from urllib.parse import quote
    return Response(content=item["content"], media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(item['name'])}", "Cache-Control": "private, no-store"})


@router.post("/drafts/{draft_id}/record-workbook", response_model=RecordResult)
async def record_to_workbook(
    workspace_id: str,
    draft_id: str,
    payload: RecordRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_role(Role.REVIEWER))],
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> RecordResult:
    validate_csrf(request, x_csrf_token)
    verify_workspace(workspace_id, principal)
    if settings.environment != "development":
        raise HTTPException(status_code=503, detail="Production database/object-store atomic publication is not configured")
    state = store.workspace(workspace_id)
    request_fingerprint = f"{draft_id}:{payload.draft_version}:{payload.workbook_id}:{payload.workbook_version}:{payload.mapping_version}:{payload.validation_id}:{payload.reason}:{payload.acknowledgements}"
    prior = state.idempotency.get(payload.idempotency_key)
    if prior:
        if prior[0] != request_fingerprint:
            raise HTTPException(status_code=409, detail="Idempotency key was reused with different review data")
        return RecordResult(**prior[1])
    draft = state.drafts.get(draft_id)
    workbook = state.workbooks.get(payload.workbook_id)
    validation = state.validation_runs.get(payload.validation_id)
    if draft is None or workbook is None or validation is None:
        raise HTTPException(status_code=404, detail="Draft, workbook, or validation run not found")
    if draft.get("target_workbook_id") and draft["target_workbook_id"] != payload.workbook_id:
        raise HTTPException(status_code=409, detail="Draft is already targeted at a different workbook")
    if not state.mappings.get(payload.workbook_id):
        raise HTTPException(status_code=422, detail="Workbook mapping is required before recording")
    if draft["version"] != payload.draft_version or validation["draft_version"] != draft["version"] or workbook["version"] != payload.workbook_version:
        raise HTTPException(status_code=409, detail="Reviewed data changed; reload and validate again")
    if draft.get("validation_stale"):
        raise HTTPException(status_code=409, detail="Draft validation is stale; run checks again")
    current_mapping = store.workspace(workspace_id).mappings.get(payload.workbook_id)
    if current_mapping is None or current_mapping.get("version") != payload.mapping_version:
        raise HTTPException(status_code=409, detail="Workbook mapping changed; review the destination again")
    if validation.get("mapping_version", 0) != payload.mapping_version:
        raise HTTPException(status_code=409, detail="Validation was run for a different mapping; rerun checks")
    if not validation.get("workbook_id"):
        raise HTTPException(status_code=409, detail="Validation was not bound to a selected workbook; rerun checks")
    if validation.get("workbook_id") != payload.workbook_id or validation.get("workbook_version", 0) != payload.workbook_version:
        raise HTTPException(status_code=409, detail="Validation was run for a different workbook version; rerun checks")
    if len(payload.acknowledgements) > 50:
        raise HTTPException(status_code=422, detail="Too many warning acknowledgements")
    selected_records = read_invoice_records(workspace_id, payload.workbook_id)
    fresh_results = validate_invoice(draft["fields"], WorkspacePolicy(), list(state.records.values()), selected_records)
    if any(result.status.value == "hard_stop" for result in fresh_results):
        raise HTTPException(status_code=422, detail="A policy hard stop blocks recording")
    reviewed_signature = {(item["check"], item["status"], item["reason"]) for item in validation["results"]}
    fresh_signature = {(item.check, item.status.value, item.reason) for item in fresh_results}
    if reviewed_signature != fresh_signature:
        raise HTTPException(status_code=409, detail="Validation changed; reload and review warnings again")
    pending = [result for result in fresh_results if result.status.value in {"warning", "inconclusive"}]
    acknowledgements = {
        str(item.get("warning_id", "")): str(item.get("reason", "")).strip()
        for item in payload.acknowledgements
    }
    if any(not acknowledgements.get(result.check) for result in pending):
        raise HTTPException(status_code=422, detail="Acknowledge each warning or inconclusive check with a reason")
    if len(acknowledgements) != len(payload.acknowledgements):
        raise HTTPException(status_code=422, detail="Warning acknowledgements must have unique IDs")
    allowed_checks = {result.check for result in pending}
    if any(key not in allowed_checks for key in acknowledgements):
        raise HTTPException(status_code=422, detail="Acknowledgement does not match an active warning")
    if draft.get("recorded"):
        raise HTTPException(status_code=409, detail="Draft already recorded")
    if not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Reviewer confirmation reason is required")
    try:
        updated, row = append_invoice(workspace_id, payload.workbook_id, draft_id)
        invoice = {name: field.get("value") for name, field in draft["fields"].items()}
        result = await publication_service.publish(
            workspace_id=workspace_id,
            actor_id=principal.user_id,
            workbook_id=payload.workbook_id,
            expected_version=payload.workbook_version,
            idempotency_key=f"{payload.idempotency_key}:{payload.draft_id}",
            payload=updated,
            invoice=invoice,
            existing_records=list(state.records.values()),
            warning_acknowledgements=[{"warning_id": key, "reason": reason} for key, reason in acknowledgements.items()],
        )
        publication = result
        publication_row = row
        update_published_workbook(workspace_id, payload.workbook_id, updated, result.version, result.reference)
        workbook["version"] = result.version
        intents.finish(workspace_id, f"{payload.idempotency_key}:{payload.draft_id}", {"status": "recorded", "reference": publication.reference, "version": publication.version, "row": row})
    except VersionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for validation_result in fresh_results:
        if validation_result.status.value != "pass":
            await record_event(workspace_id, principal.user_id, "warning_acknowledged", draft_id, {"check": validation_result.check, "reason": acknowledgements.get(validation_result.check, "")})
    draft["recorded"] = True
    draft["status"] = "recorded"
    draft["target_workbook_id"] = payload.workbook_id
    draft["validation_stale"] = False
    record = {**invoice, "reference": f"{publication.reference}:row-{publication_row}"}
    state.records[record["reference"]] = record
    draft["audit"].append({"event": "recorded", "at": datetime.now(timezone.utc).isoformat(), "actor": principal.user_id, "detail": record["reference"]})
    await record_event(workspace_id, principal.user_id, "recorded_log_entry", draft_id, {"reference": record["reference"], "workbook_id": payload.workbook_id, "version": result.version, "row": row})
    response = RecordResult(status="recorded", reference=record["reference"], message="Recorded in the invoice log only; not approved or paid.")
    state.idempotency[payload.idempotency_key] = (request_fingerprint, response.model_dump(mode="json"))
    return response


@router.post("/drafts/{draft_id}/record", response_model=RecordResult)
def record_draft(workspace_id: str, draft_id: str, payload: RecordIntent, request: Request, principal: Annotated[Principal, Depends(require_role(Role.REVIEWER))], x_csrf_token: Annotated[str | None, Header()] = None) -> RecordResult:
    validate_csrf(request, x_csrf_token)
    verify_workspace(workspace_id, principal)
    if payload.draft_id != draft_id:
        raise HTTPException(status_code=422, detail="Draft ID mismatch")
    draft = store.get_draft(workspace_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft["version"] != payload.expected_version:
        raise HTTPException(status_code=409, detail="Draft changed; review it again")
    if not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Review reason is required")
    with _record_lock:
        scope = store.workspace(workspace_id)
        prior = scope.idempotency.get(payload.idempotency_key)
        fingerprint = f"{draft_id}:{draft['version']}:{payload.reason}"
        if prior:
            if prior[0] != fingerprint:
                raise HTTPException(status_code=409, detail="Idempotency key was used for a different request")
            return RecordResult(**prior[1])
        if draft["recorded"]:
            raise HTTPException(status_code=409, detail="Draft has already been recorded")
        if settings.environment != "development":
            raise HTTPException(status_code=503, detail="Durable publication service is not configured")
        record_id = f"demo-row-{secrets.token_hex(4)}"
        now = datetime.now(timezone.utc)
        result = RecordResult(status="recorded", reference=record_id, message="Recorded in the local demo log only. This is not invoice approval or payment.", timestamp=now)
        scope.records[record_id] = {"draft_id": draft_id, "fields": draft["fields"], "timestamp": now.isoformat()}
        scope.idempotency[payload.idempotency_key] = (fingerprint, result.model_dump(mode="json"))
        draft["recorded"] = True
        draft["status"] = "recorded"
        draft["audit"].append({"event": "recorded_demo", "at": now.isoformat(), "actor": principal.user_id, "detail": f"{record_id}; reviewer reason supplied."})
        return result


@router.get("/records")
def list_records(workspace_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    items = [{"reference": key, **value} for key, value in store.workspace(workspace_id).records.items()]
    return {"items": items, "total": len(items)}


@router.get("/policy")
def get_policy(workspace_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    value = store.workspace(workspace_id).policy
    if value:
        return value
    policy = WorkspacePolicy()
    return {
        "version": policy.version,
        "required_fields": list(policy.required_fields),
        "hard_stop_fields": list(policy.hard_stop_fields),
        "allowed_overrides": list(policy.allowed_overrides),
        "currency_tolerance": {key: str(amount) for key, amount in policy.currency_tolerance.items()},
        "rounding": policy.rounding,
        "min_uncertainty_confidence": str(policy.min_uncertainty_confidence),
    }


@router.put("/policy")
def put_policy(
    workspace_id: str,
    payload: PolicyUpdateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_role(Role.ADMINISTRATOR))],
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> dict:
    validate_csrf(request, x_csrf_token)
    verify_workspace(workspace_id, principal)
    current = store.workspace(workspace_id).policy
    current_version = int(current.get("version", 1)) if current else 1
    if payload.expected_version != current_version:
        raise HTTPException(status_code=409, detail="Policy version changed; reload before editing")
    if settings.environment != "development":
        raise HTTPException(status_code=503, detail="Production policy persistence and change review are not configured")
    try:
        updated = validate_policy_update(payload.payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    data = {
        "version": current_version + 1,
        "required_fields": list(updated.required_fields),
        "hard_stop_fields": list(updated.hard_stop_fields),
        "allowed_overrides": list(updated.allowed_overrides),
        "currency_tolerance": {key: str(value) for key, value in updated.currency_tolerance.items()},
        "rounding": updated.rounding,
        "min_uncertainty_confidence": str(updated.min_uncertainty_confidence),
    }
    store.workspace(workspace_id).policy = data
    return data


@router.get("/drafts/{draft_id}/audit")
def get_audit(workspace_id: str, draft_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    draft = store.get_draft(workspace_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    from invoice_assistant.persistence.audit_repository import repository
    persisted = [event for event in repository.events if event["workspace_id"] == workspace_id and event["resource_id"] == draft_id]
    return {"items": [*draft["audit"], *persisted]}


@router.get("/workbooks/{workbook_id}/audit")
def get_workbook_audit(workspace_id: str, workbook_id: str, principal: CurrentPrincipal) -> dict:
    verify_workspace(workspace_id, principal)
    if workbook_id not in store.workspace(workspace_id).workbooks:
        raise HTTPException(status_code=404, detail="Workbook not found")
    from invoice_assistant.persistence.audit_repository import repository
    persisted = [event for event in repository.events if event["workspace_id"] == workspace_id and event.get("details", {}).get("workbook_id") == workbook_id]
    return {"items": persisted}


@router.get("/history")
def get_history(workspace_id: str, principal: CurrentPrincipal, status: Annotated[str | None, Query(max_length=32)] = None, query: Annotated[str | None, Query(max_length=128)] = None, limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0) -> dict:
    verify_workspace(workspace_id, principal)
    items = list(store.workspace(workspace_id).drafts.values())
    for item in items:
        record = next((record for record in store.workspace(workspace_id).records.values() if record.get("draft_id") == item["id"]), None)
        if record:
            item["reference"] = record.get("reference")
        else:
            item.pop("reference", None)
    if status:
        items = [item for item in items if item.get("status") == status]
    if query:
        term = query.casefold()
        items = [item for item in items if term in item.get("filename", "").casefold() or any(term in str(field.get("value") or "").casefold() for field in item.get("fields", {}).values())]
    total = len(items)
    return {"items": items[offset : offset + limit], "limit": limit, "offset": offset, "total": total}
