"""Picks the storage adapter from configuration — R2 when credentials exist, memory otherwise."""
from functools import lru_cache

from app.core.config import get_settings
from app.services.storage.base import ObjectStorage
from app.services.storage.memory import InMemoryStorage
from app.services.storage.r2 import R2Storage


@lru_cache
def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    if all(
        [
            settings.r2_endpoint_url,
            settings.r2_access_key_id,
            settings.r2_secret_access_key,
            settings.r2_bucket_name,
            settings.r2_public_base_url,
        ]
    ):
        return R2Storage(
            endpoint_url=str(settings.r2_endpoint_url),
            access_key_id=str(settings.r2_access_key_id),
            secret_access_key=str(settings.r2_secret_access_key),
            bucket_name=str(settings.r2_bucket_name),
            public_base_url=str(settings.r2_public_base_url),
        )
    return InMemoryStorage()
