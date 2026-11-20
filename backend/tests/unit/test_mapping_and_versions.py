import pytest

from invoice_assistant.persistence.object_store import MemoryObjectStore
from invoice_assistant.workbooks.mapping_service import MappingStore
from invoice_assistant.workbooks.version_store import VersionConflict, WorkbookVersionStore


def test_mapping_scopes_to_workspace_and_detects_header_changes():
    store = MappingStore()
    record = store.save("ws-a", "book", "Invoices", ["Vendor", "Invoice"], {"vendor_name": 1, "invoice_number": 2}, ["vendor_name"])
    assert store.get("ws-b", "book") is None
    assert store.validate_current_headers(record, ["Vendor", "Invoice"])
    assert not store.validate_current_headers(record, ["Invoice", "Vendor"])


def test_mapping_rejects_missing_required_and_duplicate_columns():
    store = MappingStore()
    with pytest.raises(ValueError, match="Required fields"):
        store.save("ws", "book", "Invoices", ["Vendor"], {}, ["vendor_name"])
    with pytest.raises(ValueError, match="different workbook column"):
        store.save("ws", "book", "Invoices", ["Vendor", "Invoice"], {"vendor_name": 1, "invoice_number": 1})


@pytest.mark.asyncio
async def test_version_store_stages_and_compare_and_swap_publishes_once():
    store = WorkbookVersionStore(MemoryObjectStore())
    staged = await store.stage("ws", "book", 0, b"version-one")
    store.publish(staged, expected_version=0)
    assert store.current_version("ws", "book") == 1
    with pytest.raises(VersionConflict):
        store.publish(staged, expected_version=0)
