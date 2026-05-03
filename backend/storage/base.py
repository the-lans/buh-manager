from typing import Protocol

from fastapi import UploadFile


class StorageProvider(Protocol):
    async def upload_file(self, *, file: UploadFile, file_id: str) -> str:
        """Save file and return its URL."""
        ...
