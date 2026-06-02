from pathlib import Path
from shutil import copyfileobj

from fastapi import UploadFile

from app.constants import MEDIA_PATH


class LocalStorageProvider:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or Path(MEDIA_PATH)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, *, file: UploadFile, file_id: str) -> str:
        suffix = Path(file.filename or "file").suffix or ""
        dest = self._base_dir / f"{file_id}{suffix}"
        await file.seek(0)
        with dest.open("wb") as destination:
            copyfileobj(file.file, destination)
        return f"/{MEDIA_PATH}/{file_id}{suffix}"

    async def delete_file(self, *, doc_url: str) -> None:
        local_path = self._base_dir / Path(doc_url).name
        local_path.unlink(missing_ok=True)

    def get_download_url(
        self, *, doc_url: str, filename: str, inline: bool = False, expires_in: int = 3600
    ) -> str:
        _ = (filename, inline, expires_in)
        return doc_url
