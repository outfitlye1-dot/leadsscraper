import math
import re
import uuid
from pathlib import Path

from app.core.config import get_settings


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^\w\s\-.]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name or "upload"


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_user_upload_path(user_id: int, filename: str) -> Path:
    settings = get_settings()
    safe_name = sanitize_filename(filename)
    user_dir = ensure_directory(Path(settings.UPLOAD_DIR) / str(user_id))
    return user_dir / f"{uuid.uuid4().hex}_{safe_name}"


def validate_file_extension(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    return None
