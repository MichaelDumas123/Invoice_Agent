"""OpenRouter extraction adapter; fails closed unless an administrator approved it."""

from typing import Any

from invoice_assistant.config import settings
from invoice_assistant.documents.extraction_provider import ProviderNotApproved


class OpenRouterExtractor:
    def __init__(self) -> None:
        self.model_name = settings.model_name

    async def extract(self, pages: list[bytes]) -> dict[str, Any]:
        if not pages:
            raise ValueError("At least one processed page is required")
        if not settings.provider_approved:
            raise ProviderNotApproved("OpenRouter processing is disabled until organizational approval")
        if settings.model_name != "qwen/qwen3.7-flash":
            raise ProviderNotApproved("Configured model differs from the approved model target")
        if not settings.model_api_key:
            raise ProviderNotApproved("OpenRouter credentials are not configured")
        raise ProviderNotApproved("Live image extraction is not enabled in this prototype; capability verification is required")
