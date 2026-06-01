from typing import Protocol

from fastapi import UploadFile


class StorageProvider(Protocol):
    async def upload_file(self, *, file: UploadFile, file_id: str) -> str:
        """Save file and return its URL."""
        ...

    async def delete_file(self, *, doc_url: str) -> None:
        """Delete a previously saved file if it exists."""
        ...

    def get_download_url(
        self, *, doc_url: str, filename: str, inline: bool = False, expires_in: int = 3600
    ) -> str:
        """Return a URL for downloading/viewing the file."""
        ...
