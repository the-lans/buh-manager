from pathlib import Path

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
