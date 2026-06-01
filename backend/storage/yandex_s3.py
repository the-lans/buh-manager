import mimetypes
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import boto3
from fastapi import UploadFile

from app.config import settings
from app.constants import S3_ENDPOINT_URL


class YandexS3Provider:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=settings.yandex_access_key,
            aws_secret_access_key=settings.yandex_secret_key,
            region_name="ru-central1",
        )
        self._bucket = settings.yandex_s3_bucket

    async def upload_file(self, *, file: UploadFile, file_id: str) -> str:
        suffix = Path(file.filename or "file").suffix or ""
        filename = f"{file_id}{suffix}"
        content = await file.read()
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=filename,
                Body=content,
                ContentType=file.content_type or "application/octet-stream",
            )
        except Exception as exc:
            raise RuntimeError(f"S3 upload failed: {exc}") from exc
        return f"https://{self._bucket}.storage.yandexcloud.net/{filename}"

    async def delete_file(self, *, doc_url: str) -> None:
        key = Path(urlparse(doc_url).path).name
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            raise RuntimeError(f"S3 delete failed: {exc}") from exc

    def get_download_url(
        self, *, doc_url: str, filename: str, inline: bool = False, expires_in: int = 3600
    ) -> str:
        key = Path(urlparse(doc_url).path).name
        quoted = filename.replace('"', "_")
        disposition = (
            f'inline; filename="{quoted}"' if inline else f'attachment; filename="{quoted}"'
        )
        params: dict[str, str] = {
            "Bucket": self._bucket,
            "Key": key,
            "ResponseContentDisposition": disposition,
        }
        if inline:
            content_type, _ = mimetypes.guess_type(filename)
            if content_type:
                params["ResponseContentType"] = content_type
        try:
            return cast(
                str,
                self._client.generate_presigned_url(
                    "get_object",
                    Params=params,
                    ExpiresIn=expires_in,
                ),
            )
        except Exception as exc:
            raise RuntimeError(f"S3 presign failed: {exc}") from exc
