import asyncio
import uuid
from pathlib import Path

from fastapi import UploadFile

from src.config import settings


async def save_upload_file(file: UploadFile) -> tuple[Path, int]:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "file").suffix
    stored_path = upload_dir / f"{uuid.uuid4()}{suffix}"

    data = await file.read()
    await asyncio.to_thread(stored_path.write_bytes, data)

    return stored_path, len(data)
