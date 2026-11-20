"""Bounded PDF/image/HEIC rendering for small documents.

Production worker isolation and process-level CPU/memory/network limits are still
required; this module enforces document/page/pixel caps before returning page data.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import fitz  # type: ignore[import-untyped]
from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from invoice_assistant.documents.intake import UploadedDocument

MAX_PAGES = 100
MAX_PIXELS = 30_000_000
PDF_DPI = 120
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
warnings.filterwarnings("error", category=Image.DecompressionBombWarning)

try:
    from pillow_heif import register_heif_opener  # type: ignore[import-untyped]
    register_heif_opener()
except ImportError:
    pass


@dataclass(frozen=True)
class RenderedPage:
    page: int
    image_png: bytes | None
    width: int | None
    height: int | None
    status: str
    error: str | None = None


def _png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def convert_document(document: UploadedDocument) -> list[RenderedPage]:
    if document.detected_type == "application/pdf":
        return _convert_pdf(document.content)
    return [_convert_image(document.content)]


def _convert_pdf(content: bytes) -> list[RenderedPage]:
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError("PDF could not be opened safely") from exc
    pages: list[RenderedPage] = []
    try:
        if pdf.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")
        if len(pdf) < 1 or len(pdf) > MAX_PAGES:
            raise ValueError(f"PDF page count must be between 1 and {MAX_PAGES}")
        scale = PDF_DPI / 72
        matrix = fitz.Matrix(scale, scale)
        for page_index in range(len(pdf)):
            try:
                pixmap = pdf[page_index].get_pixmap(matrix=matrix, alpha=False, annots=False)
                if pixmap.width * pixmap.height > MAX_PIXELS:
                    pages.append(RenderedPage(page_index + 1, None, pixmap.width, pixmap.height, "failed", "Rendered page exceeds pixel limit"))
                    continue
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                pages.append(RenderedPage(page_index + 1, _png(image), pixmap.width, pixmap.height, "processed"))
            except Exception:
                pages.append(RenderedPage(page_index + 1, None, None, None, "failed", "Page render failed"))
    finally:
        pdf.close()
    return pages


def _convert_image(content: bytes) -> RenderedPage:
    try:
        opened = Image.open(BytesIO(content))
        image = ImageOps.exif_transpose(opened)
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, DecompressionBombError) as exc:
        raise ValueError("Image could not be decoded") from exc
    if image.width * image.height > MAX_PIXELS:
        raise ValueError("Image exceeds pixel limit")
    if getattr(image, "n_frames", 1) > 1:
        image.seek(0)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")
    elif image.mode == "RGBA":
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        image = background
    return RenderedPage(1, _png(image), image.width, image.height, "processed")


def page_summaries(pages: list[RenderedPage]) -> list[dict[str, Any]]:
    return [{"page": page.page, "status": page.status, "width": page.width, "height": page.height, "error": page.error} for page in pages]
