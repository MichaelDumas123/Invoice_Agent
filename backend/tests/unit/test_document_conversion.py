from io import BytesIO

import fitz
from PIL import Image

from invoice_assistant.documents.conversion import convert_document
from invoice_assistant.documents.intake import validate_document


def pdf_bytes(pages: int = 2) -> bytes:
    document = fitz.open()
    for _ in range(pages):
        page = document.new_page(width=300, height=200)
        page.insert_text((20, 30), "Synthetic invoice page")
    data = document.tobytes()
    document.close()
    return data


def test_multi_page_pdf_renders_each_page_to_png():
    checked = validate_document("sample.pdf", "application/pdf", pdf_bytes(2), 2_000_000)
    pages = convert_document(checked)
    assert [page.status for page in pages] == ["processed", "processed"]
    assert all(page.image_png and page.width and page.height for page in pages)


def test_png_conversion_returns_reencoded_png():
    image = Image.new("RGB", (80, 40), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    checked = validate_document("sample.png", "image/png", output.getvalue(), 2_000_000)
    page = convert_document(checked)[0]
    assert page.status == "processed"
    assert page.image_png.startswith(b"\x89PNG")


def test_heic_conversion_when_decoder_is_available():
    import pillow_heif

    image = Image.new("RGB", (24, 16), "white")
    output = BytesIO()
    pillow_heif.from_pillow(image).save(output, format="HEIF")
    checked = validate_document("sample.heic", "image/heif", output.getvalue(), 2_000_000)
    page = convert_document(checked)[0]
    assert page.status == "processed"
    assert page.image_png.startswith(b"\x89PNG")


def test_page_limit_rejects_excessively_long_pdf():
    from invoice_assistant.documents.conversion import MAX_PAGES
    checked = validate_document("sample.pdf", "application/pdf", pdf_bytes(MAX_PAGES + 1), 40_000_000)
    try:
        convert_document(checked)
    except ValueError as exc:
        assert "page count" in str(exc)
    else:
        raise AssertionError("expected page count limit")
