"""Conservative document validation for the local development MVP."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UploadedDocument:
    filename: str
    content_type: str
    content: bytes
    detected_type: str


SIGNATURES = {
    b"%PDF-": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\x00\x00\x00\x18ftypheic": "image/heic",
    b"\x00\x00\x00\x1cftypheic": "image/heic",
    b"\x00\x00\x00\x18ftypheix": "image/heic",
    b"\x00\x00\x00\x1cftypheix": "image/heic",
    b"\x00\x00\x00\x18ftypmif1": "image/heif",
    b"\x00\x00\x00\x1cftypmif1": "image/heif",
}

ALLOWED = {"application/pdf", "image/jpeg", "image/png", "image/heic", "image/heif"}


def detect_type(content: bytes, filename: str) -> str | None:
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        brand = content[8:12]
        if brand in {b"heic", b"heix", b"hevc", b"hevx"}:
            return "image/heif" if b"mif1" in content[8:64] or b"msf1" in content[8:64] else "image/heic"
        if brand in {b"mif1", b"msf1"} or b"mif1" in content[8:64] or b"msf1" in content[8:64]:
            return "image/heif"
    return None


def declared_type_supported(content_type: str) -> bool:
    return not content_type or content_type in ALLOWED or content_type == "application/octet-stream"


def validate_document(filename: str, content_type: str, content: bytes, max_bytes: int) -> UploadedDocument:
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > max_bytes:
        raise OverflowError(f"The file exceeds the {max_bytes} byte upload limit.")
    if content.startswith(b"%PDF-"):
        if b"/Encrypt" in content:
            raise ValueError("Encrypted PDFs are not supported")
    detected = detect_type(content, filename)
    if detected is None or detected not in ALLOWED:
        raise TypeError("Unsupported or unrecognized invoice file. Upload PDF, JPEG, PNG, HEIC, or HEIF.")
    if not declared_type_supported(content_type):
        raise TypeError("The declared media type is not supported.")
    if content_type and content_type not in {detected, "application/octet-stream"}:
        raise TypeError("The file content does not match its declared media type.")
    if detected == "application/pdf" and b"%%EOF" not in content[-2048:]:
        raise ValueError("The PDF appears incomplete or malformed.")
    safe_name = filename.replace("\\", "/").split("/")[-1][:255] or "invoice"
    return UploadedDocument(filename=safe_name, content_type=detected, content=content, detected_type=detected)
