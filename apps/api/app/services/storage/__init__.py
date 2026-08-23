"""Object storage abstraction. The API never writes uploads to the container filesystem."""
from app.services.storage.base import ObjectStorage, StoredObject, UploadValidationError
from app.services.storage.factory import get_object_storage
from app.services.storage.memory import InMemoryStorage
from app.services.storage.r2 import R2Storage

__all__ = [
    "InMemoryStorage",
    "ObjectStorage",
    "R2Storage",
    "StoredObject",
    "UploadValidationError",
    "get_object_storage",
]
