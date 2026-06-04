from typing import Any, BinaryIO

from contextlib import asynccontextmanager

from aiobotocore.session import get_session
from botocore.exceptions import ClientError

from ...shared.domain.exceptions import NotFoundError
from ..domain.ports import Storage


class S3Storage(Storage):
    def __init__(
            self,
            access_key: str,
            secret_key: str,
            endpoint_url: str,
            bucket_name: str,
    ) -> None:
        self.config = {
            "service_name": "s3",
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
        }
        self.bucket_name = bucket_name
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self):
        async with self.session.create_client(**self.config) as client:
            yield client

    async def upload(self, file: BinaryIO, storage_key: str, content_type: str) -> None:
        async with self.get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Body=file.read(),
                Key=storage_key,
                ContentType=content_type,
            )

    async def delete(self, storage_key: str) -> None:
        async with self.get_client() as client:
            await client.delete_object(Bucket=self.bucket_name, Key=storage_key)

    async def create_presigned_upload_url(
            self, storage_key: str, content_type: str, expires_in: int = 3600
    ) -> str:
        async with self.get_client() as client:
            return await client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name, "Key": storage_key, "ContentType": content_type
                },
                ExpiresIn=expires_in,
                HttpMethod="PUT",
            )

    async def create_presigned_download_url(self, storage_key: str, expires_in: int = 3600) -> str:
        async with self.get_client() as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": storage_key},
                ExpiresIn=expires_in,
                HttpMethod="GET",
            )

    async def get_file_info(self, storage_key: str) -> dict[str, Any]:
        try:
            async with self.get_client() as client:
                response = await client.head_object(Bucket=self.bucket_name, Key=storage_key)
                return {
                    "size": response["ContentLength"],
                    "content_type": response["ContentType"],
                    "uploaded_at": response["LastModified"],
                }
        except ClientError:
            raise NotFoundError(f"File not found by key - {storage_key}") from None
