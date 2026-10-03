"""Disk storage for uploaded files.

Files are stored under UPLOAD_DIR with a random name, so nothing supplied by
the client (file name, declared content type) decides where or how they are
written. The type is detected from the first bytes of the content.
"""

import os
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.errors import FileTooLargeError, UnsupportedFileError

MAX_FILE_BYTES = 20 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024


def upload_dir() -> Path:
    return Path(os.environ.get("UPLOAD_DIR", "uploads")).resolve()


def detect_type(head: bytes) -> tuple[str, str] | None:
    """Returns (mime_type, extension) for the supported formats, else None."""
    if head.startswith(b"%PDF-"):
        return "application/pdf", ".pdf"

    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"

    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"

    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", ".webp"

    return None


def store(stream: BinaryIO) -> tuple[str, str, int]:
    """Writes the stream to disk. Returns (stored_name, mime_type, size_bytes)."""
    head = stream.read(16)
    detected = detect_type(head)

    if detected is None:
        raise UnsupportedFileError("Only PDF, PNG, JPEG and WebP files are supported")

    mime_type, extension = detected
    stored_name = f"{uuid4().hex}{extension}"
    directory = upload_dir()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / stored_name
    size = 0

    try:
        with target.open("wb") as output:
            chunk = head

            while chunk:
                size += len(chunk)

                if size > MAX_FILE_BYTES:
                    raise FileTooLargeError(
                        f"File exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB limit"
                    )

                output.write(chunk)
                chunk = stream.read(CHUNK_BYTES)
    except BaseException:
        target.unlink(missing_ok=True)
        raise

    return stored_name, mime_type, size


def path_for(stored_name: str) -> Path:
    # stored_name comes from the database; Path.name guards against a tampered row.
    return upload_dir() / Path(stored_name).name


def remove(stored_name: str) -> None:
    path_for(stored_name).unlink(missing_ok=True)
