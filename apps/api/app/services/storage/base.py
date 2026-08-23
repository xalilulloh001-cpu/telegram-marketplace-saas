"""Storage contract plus upload validation shared by every adapter."""
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Extension is derived from the declared MIME type, never from the uploaded filename,
# so a file called "evil.php.jpg" cannot smuggle an extension through.
ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class UploadValidationError(Exception):
    """Raised when an upload fails validation before it reaches storage."""


@dataclass(frozen=True)
class StoredObject:
    key: str
    url: str


def validate_image(content_type: str | None, size_bytes: int) -> str:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise UploadValidationError("unsupported image type")
    if size_bytes <= 0:
        raise UploadValidationError("empty file")
    if size_bytes > MAX_IMAGE_BYTES:
        raise UploadValidationError("file is too large")
    return ALLOWED_IMAGE_TYPES[content_type]


def build_key(shop_id: int, product_id: int, extension: str) -> str:
    """Tenant-aware key: shops can never collide, and the name is server-generated."""
    return f"shops/{shop_id}/products/{product_id}/{uuid.uuid4().hex}.{extension}"


class ObjectStorage(ABC):
    @abstractmethod
    async def upload(
        self, key: str, data: bytes, content_type: str
    ) -> StoredObject:  # pragma: no cover - interface
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:  # pragma: no cover - interface
        ...
