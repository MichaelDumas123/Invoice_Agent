"""Extraction provider protocol with external processing disabled by default."""

from typing import Any, Protocol


class ExtractionProvider(Protocol):
    async def extract(self, pages: list[bytes]) -> dict[str, Any]: ...


class ProviderNotApproved(RuntimeError):
    pass


class DisabledProvider:
    async def extract(self, pages: list[bytes]) -> dict[str, Any]:
        raise ProviderNotApproved("External invoice extraction is disabled until provider and privacy approval")


provider: ExtractionProvider = DisabledProvider()
