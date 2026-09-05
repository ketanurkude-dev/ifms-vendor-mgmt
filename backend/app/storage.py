"""Local disk storage for uploaded documents. Stands in for the IFMS
Document Management System (INT-VEP-010) -- files really are written to
and read back from disk (not just a filename recorded), which is as far
as a prototype can reasonably go without a real DMS integration."""

import uuid
from pathlib import Path

from fastapi import UploadFile

UPLOAD_ROOT = Path(__file__).parent / "uploads"
ALLOWED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_upload(file: UploadFile) -> None:
    from fastapi import HTTPException, status

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF, JPG, JPEG, or PNG files are accepted")


def save_upload(file: UploadFile, subfolder: str, contents: bytes) -> str:
    """Writes the file to disk under uploads/<subfolder>/ with a random
    name (so two vendors uploading "pan.pdf" never collide) and returns
    the path stored on the document row."""
    if len(contents) > MAX_FILE_SIZE_BYTES:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds the 10 MB size limit")

    folder = UPLOAD_ROOT / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    (folder / stored_name).write_bytes(contents)
    return f"{subfolder}/{stored_name}"


def read_stored_file(stored_path: str) -> bytes:
    return (UPLOAD_ROOT / stored_path).read_bytes()


MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def guess_media_type(file_name: str) -> str:
    """Content-type for viewing a file inline in the browser. Falls back
    to a generic download type for anything outside ALLOWED_EXTENSIONS."""
    return MEDIA_TYPES.get(Path(file_name).suffix.lower(), "application/octet-stream")
