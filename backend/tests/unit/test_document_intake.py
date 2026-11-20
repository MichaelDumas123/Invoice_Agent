import pytest

from invoice_assistant.documents.intake import validate_document


@pytest.mark.parametrize(
    ("filename", "media_type", "content", "expected"),
    [
        ("invoice.pdf", "application/pdf", b"%PDF-1.4\n%%EOF", "application/pdf"),
        ("invoice.jpg", "image/jpeg", b"\xff\xd8\xffdata", "image/jpeg"),
        ("invoice.png", "image/png", b"\x89PNG\r\n\x1a\ndata", "image/png"),
        ("invoice.heic", "image/heic", b"\x00\x00\x00\x18ftypheicdata", "image/heic"),
    ],
)
def test_supported_signatures(filename, media_type, content, expected):
    result = validate_document(filename, media_type, content, max_bytes=1024)
    assert result.detected_type == expected
    assert result.filename == filename


def test_empty_file_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        validate_document("invoice.pdf", "application/pdf", b"", max_bytes=1024)


def test_oversized_file_is_rejected():
    with pytest.raises(OverflowError, match="upload limit"):
        validate_document("invoice.pdf", "application/pdf", b"%PDF-1.4\n%%EOF", max_bytes=4)


def test_mime_mismatch_is_rejected():
    with pytest.raises(TypeError, match="declared media type"):
        validate_document("invoice.png", "image/png", b"%PDF-1.4\n%%EOF", max_bytes=1024)


def test_filename_traversal_is_reduced_to_basename():
    result = validate_document("../../invoice.pdf", "application/pdf", b"%PDF-1.4\n%%EOF", max_bytes=1024)
    assert result.filename == "invoice.pdf"


def test_encrypted_pdf_is_rejected():
    with pytest.raises(ValueError, match="Encrypted PDFs"):
        validate_document("invoice.pdf", "application/pdf", b"%PDF-1.4 /Encrypt %%EOF", max_bytes=1024)
