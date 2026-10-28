import asyncio
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from src.application.upload_validation import ValidateUpload
from src.config import settings
from src.domain.uploads import DocxLimits, UploadRejected
from src.infrastructure.docx_inspector import DocxInspector

_CHUNK = 1024 * 1024


def validate_extension(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in settings.allowed_extensions:
        allowed = ", ".join(sorted(settings.allowed_extensions))
        raise HTTPException(
            status_code=415,
            detail=f"Формат «{suffix or 'без расширения'}» не поддерживается. Допустимо: {allowed}",
        )
    return suffix


def _validate_stored_docx(path: Path) -> None:
    validator = ValidateUpload(
        DocxInspector(), DocxLimits(max_compressed_bytes=settings.UPLOAD_MAX_MB * 1024 * 1024)
    )
    with path.open("rb") as source:
        validator.execute(source, ".docx")


async def save_upload_file(file: UploadFile) -> tuple[Path, int]:
    """Stream the upload to disk with a size cap; the file name on disk is random."""
    suffix = validate_extension(file.filename)
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{uuid.uuid4()}{suffix}"
    limit = settings.UPLOAD_MAX_MB * 1024 * 1024

    size = 0
    try:
        with stored_path.open("wb") as out:
            while chunk := await file.read(_CHUNK):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Файл «{file.filename}» больше {settings.UPLOAD_MAX_MB} МБ",
                    )
                out.write(chunk)
        if suffix == ".docx":
            try:
                await asyncio.to_thread(_validate_stored_docx, stored_path)
            except UploadRejected as exc:
                status = 413 if exc.code == "docx_limit" else 415
                raise HTTPException(status, str(exc)) from None
    except BaseException:
        stored_path.unlink(missing_ok=True)
        raise

    return stored_path, size
