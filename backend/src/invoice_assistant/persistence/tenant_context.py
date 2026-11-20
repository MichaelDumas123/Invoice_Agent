"""Workspace transaction-scoped RLS context helper."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from invoice_assistant.persistence.database import Database


@asynccontextmanager
async def workspace_transaction(database: Database, workspace_id: str) -> AsyncIterator[object | None]:
    if not workspace_id:
        raise ValueError("workspace_id is required")
    async with database.transaction(workspace_id) as connection:
        yield connection
