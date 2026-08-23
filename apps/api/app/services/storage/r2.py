"""Cloudflare R2 adapter (S3-compatible). Credentials come from the environment only."""
from app.services.storage.base import ObjectStorage, StoredObject


class R2Storage(ObjectStorage):
    def __init__(
        self,
        endpoint_url: str,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        public_base_url: str,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._bucket_name = bucket_name
        self._public_base_url = public_base_url.rstrip("/")

    def _client(self):
        import boto3  # imported lazily so the dependency is optional until R2 is used

        return boto3.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
        )

    async def upload(self, key: str, data: bytes, content_type: str) -> StoredObject:
        self._client().put_object(
            Bucket=self._bucket_name, Key=key, Body=data, ContentType=content_type
        )
        return StoredObject(key=key, url=f"{self._public_base_url}/{key}")

    async def delete(self, key: str) -> None:
        self._client().delete_object(Bucket=self._bucket_name, Key=key)
