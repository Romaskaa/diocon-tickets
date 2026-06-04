import io
from uuid import uuid4

import aiohttp
import pytest
from fastapi import status

from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def storage_key() -> str:
    return f"test-file-{uuid4()}.txt"


@pytest.fixture
def file_bytes() -> bytes:
    return b"Hello, MinIO! This is a test file."


class TestS3Storage:
    @pytest.mark.asyncio
    async def test_upload_and_get_file_info(self, s3_storage, storage_key, file_bytes):
        file = io.BytesIO(file_bytes)
        content_type = "text/plain"

        await s3_storage.upload(file, storage_key=storage_key, content_type=content_type)

        file_info = await s3_storage.get_file_info(storage_key)

        assert file_info["size"] == len(file_bytes)
        assert file_info["content_type"] == content_type
        assert file_info["uploaded_at"] is not None

    @pytest.mark.asyncio
    async def test_delete(self, s3_storage, storage_key, file_bytes):
        file = io.BytesIO(file_bytes)
        content_type = "text/plain"

        await s3_storage.upload(file, storage_key=storage_key, content_type=content_type)

        await s3_storage.delete(storage_key)

        with pytest.raises(NotFoundError):
            await s3_storage.get_file_info(storage_key)

    @pytest.mark.asyncio
    async def test_presigned_upload_url(self, s3_storage, storage_key, file_bytes):
        content_type = "text/plain"
        url = await s3_storage.create_presigned_upload_url(
            storage_key, content_type, expires_in=60
        )

        async with aiohttp.ClientSession() as session, session.put(
            url=url, data=file_bytes, headers={"Content-Type": content_type}
        ) as response:
            assert response.status == status.HTTP_200_OK

        file_info = await s3_storage.get_file_info(storage_key)

        assert file_info["size"] == len(file_bytes)
        assert file_info["content_type"] == content_type

    @pytest.mark.asyncio
    async def test_presigned_download_url(self, s3_storage, storage_key, file_bytes):
        file = io.BytesIO(file_bytes)
        content_type = "text/plain"

        await s3_storage.upload(file, storage_key=storage_key, content_type=content_type)

        url = await s3_storage.create_presigned_download_url(storage_key, expires_in=60)

        async with aiohttp.ClientSession() as session, session.get(url=url) as response:
            assert response.status == status.HTTP_200_OK
            downloaded_file = await response.read()

        assert downloaded_file == file_bytes

    @pytest.mark.asyncio
    async def test_file_info_non_exists(self, s3_storage):
        with pytest.raises(NotFoundError):
            await s3_storage.get_file_info("non-existent-key-12345")
