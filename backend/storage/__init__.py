from app.config import settings
from storage.base import StorageProvider
from storage.local import LocalStorageProvider
from storage.yandex_s3 import YandexS3Provider


def get_storage_provider() -> StorageProvider:
    if settings.is_local:
        return LocalStorageProvider()
    return YandexS3Provider()
