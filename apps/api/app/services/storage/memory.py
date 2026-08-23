"""In-memory adapter used for local development and tests when R2 is not configured."""
from app.services.storage.base import ObjectStorage, StoredObject


class InMemoryStorage(ObjectStorage):
    def __init__(self, public_base_url: str = "https://storage.local") -> None:
        self._public_base_url = public_base_url.rstrip("/")
        self.objects: dict[str, bytes] = {}

    async def upload(self, key: str, data: bytes, content_type: str) -> StoredObject:
        self.objects[key] = data
        return StoredObject(key=key, url=f"{self._public_base_url}/{key}")

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)
