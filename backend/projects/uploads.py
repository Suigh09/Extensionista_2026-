"""Shared upload validation (Sprint 4.8 rules, reused by deliveries in Sprint 5)."""

from pathlib import Path
from zipfile import BadZipFile, ZipFile

from rest_framework.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".txt",
    ".csv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".zip",
}
BLOCKED_CONTENT_TYPES = {
    "application/x-msdownload",
    "application/x-executable",
    "application/x-sh",
    "text/x-python",
}
DETECTED_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".zip": "application/zip",
}

MAX_UPLOAD_SIZE = 25 * 1024 * 1024


def valid_signature(uploaded, extension):
    header = uploaded.read(16)
    uploaded.seek(0)
    signatures = {
        ".pdf": (b"%PDF-",),
        ".png": (b"\x89PNG\r\n\x1a\n",),
        ".jpg": (b"\xff\xd8\xff",),
        ".jpeg": (b"\xff\xd8\xff",),
        ".webp": (b"RIFF",),
        ".zip": (b"PK\x03\x04", b"PK\x05\x06"),
        ".docx": (b"PK\x03\x04",),
        ".xlsx": (b"PK\x03\x04",),
        ".pptx": (b"PK\x03\x04",),
    }
    if extension in {".txt", ".csv"}:
        try:
            header.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return any(header.startswith(signature) for signature in signatures.get(extension, ()))


def valid_zip_structure(uploaded, extension):
    if extension not in {".zip", ".docx", ".xlsx", ".pptx"}:
        return True
    required = {
        ".docx": {"[Content_Types].xml", "_rels/.rels", "word/document.xml"},
        ".xlsx": {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"},
        ".pptx": {"[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml"},
    }
    try:
        with ZipFile(uploaded) as archive:
            entries = archive.infolist()
            names = {entry.filename.replace("\\", "/") for entry in entries}
            total_size = sum(entry.file_size for entry in entries)
            if len(entries) > 1000 or total_size > 100 * 1024 * 1024:
                return False
            for entry in entries:
                if entry.flag_bits & 0x1 or entry.filename.lower().endswith(
                    "vbaproject.bin"
                ):
                    return False
                if (
                    entry.file_size > 1024 * 1024
                    and entry.compress_size
                    and entry.file_size / entry.compress_size > 200
                ):
                    return False
            return required.get(extension, set()).issubset(names)
    except (BadZipFile, OSError, ValueError):
        return False
    finally:
        uploaded.seek(0)


def sanitize_filename(name):
    return Path(name).name[:255]


def validate_upload(uploaded, *, field_name="arquivo"):
    """Validate a single uploaded document; return (safe_name, content_type, size)."""
    suffixes = Path(uploaded.name).suffixes
    extension = Path(uploaded.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS or len(suffixes) > 1:
        raise ValidationError(f"Formato não permitido: {uploaded.name}")
    if uploaded.size > MAX_UPLOAD_SIZE:
        raise ValidationError(f"O arquivo {uploaded.name} ultrapassa 25 MB.")
    content_type = (uploaded.content_type or "application/octet-stream").lower()
    if content_type in BLOCKED_CONTENT_TYPES:
        raise ValidationError(f"Conteúdo de arquivo não permitido: {uploaded.name}")
    if not valid_signature(uploaded, extension):
        raise ValidationError(
            f"O conteúdo não corresponde ao formato informado: {uploaded.name}"
        )
    if not valid_zip_structure(uploaded, extension):
        raise ValidationError(
            f"A estrutura interna do arquivo é inválida ou insegura: {uploaded.name}"
        )
    detected = DETECTED_CONTENT_TYPES.get(extension, "application/octet-stream")
    return sanitize_filename(uploaded.name), detected, uploaded.size
