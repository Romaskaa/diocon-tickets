from uuid import uuid4

import aiohttp
import pytest
from fastapi import status

from src.media.schemas import ConfirmUploadRequest, PresignedUploadRequest
from src.media.services import AttachmentService
from src.shared.domain.exceptions import NotFoundError


@pytest.fixture
def attachment_service(session, attachment_repo, s3_storage):
    return AttachmentService(session=session, repository=attachment_repo, storage=s3_storage)


@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
def owner_type():
    return "ticket"


@pytest.fixture
def uploaded_by():
    return uuid4()


@pytest.fixture
def sample_file_bytes():
    return b"Test file content for service"


@pytest.fixture
def original_filename():
    return "test_file.txt"


@pytest.fixture
def content_type():
    return "text/plain"


class TestAttachmentService:
    @pytest.mark.asyncio
    async def test_create_presigned_upload_url(
            self,
            attachment_service,
            owner_type,
            owner_id,
            original_filename,
            content_type,
    ):
        request = PresignedUploadRequest(
            filename=original_filename,
            content_type=content_type,
            owner_type=owner_type,
            owner_id=owner_id,
        )
        response = await attachment_service.create_presigned_upload_url(request)

        assert response.upload_url is not None
        assert response.storage_key.startswith(f"{owner_type}/{owner_id}/")
        assert response.storage_key.endswith(".txt")

    @pytest.mark.asyncio
    async def test_confirm_upload(
        self,
        attachment_repo,
        attachment_service,
        owner_type,
        owner_id,
        original_filename,
        content_type,
        uploaded_by,
        sample_file_bytes,
    ):
        # 1. Создание подписанного URL для загрузки
        upload_request = PresignedUploadRequest(
            filename=original_filename,
            content_type=content_type,
            owner_type=owner_type,
            owner_id=owner_id,
        )
        presigned_response = await attachment_service.create_presigned_upload_url(upload_request)

        # 2. Загрузка файла по подписанному URL
        async with aiohttp.ClientSession() as session, session.put(
            url=presigned_response.upload_url,
                data=sample_file_bytes,
                headers={"Content-Type": content_type},
        ) as response:
            assert response.status == status.HTTP_200_OK

        # 3. Подтверждение загрузки
        confirm_request = ConfirmUploadRequest(
            storage_key=presigned_response.storage_key,
            original_filename=original_filename,
            content_type=content_type,
            owner_type=owner_type,
            owner_id=owner_id,
        )
        confirmed_response = await attachment_service.confirm_upload(
            confirm_request, uploaded_by=uploaded_by
        )

        # 4. Проверка ответа
        assert confirmed_response.id is not None
        assert confirmed_response.original_filename == original_filename
        assert confirmed_response.mime_type == content_type
        assert confirmed_response.size_bytes == len(sample_file_bytes)
        assert confirmed_response.storage_key == presigned_response.storage_key
        assert confirmed_response.owner_type == owner_type
        assert confirmed_response.owner_id == owner_id
        assert confirmed_response.uploaded_by == uploaded_by

        # 5. Проверка того, что запись действительно создана в БД
        attachment = await attachment_repo.read(confirmed_response.id)

        assert attachment is not None
        assert attachment.storage_key == presigned_response.storage_key

    @pytest.mark.asyncio
    async def test_create_presigned_download_url_success(
            self,
            attachment_service,
            owner_type,
            owner_id,
            original_filename,
            content_type,
            uploaded_by,
            sample_file_bytes,
    ):
        # 1. Загрузка файла в хранилище
        upload_request = PresignedUploadRequest(
            filename=original_filename,
            content_type=content_type,
            owner_type=owner_type,
            owner_id=owner_id,
        )
        upload_response = await attachment_service.create_presigned_upload_url(upload_request)

        async with aiohttp.ClientSession() as session, session.put(
            upload_response.upload_url,
            data=sample_file_bytes,
            headers={"Content-Type": content_type},
        ) as resp:
            assert resp.status == status.HTTP_200_OK

        confirm_request = ConfirmUploadRequest(
            storage_key=upload_response.storage_key,
            original_filename=original_filename,
            content_type=content_type,
            owner_type=owner_type,
            owner_id=owner_id,
        )
        attachment = await attachment_service.confirm_upload(confirm_request, uploaded_by)

        # 2. Скачивание файла из хранилища
        download_response = await attachment_service.create_presigned_download_url(attachment.id)

        assert download_response.download_url is not None
        assert download_response.storage_key == upload_response.storage_key

        async with aiohttp.ClientSession() as session, session.get(
                download_response.download_url
        ) as response:
            assert response.status == status.HTTP_200_OK

            downloaded_file = await response.read()

        assert downloaded_file == sample_file_bytes

    @pytest.mark.asyncio
    async def test_create_presigned_download_url_raises_not_found(self, attachment_service):
        non_existing_attachment_id = uuid4()

        with pytest.raises(NotFoundError) as exc:
            await attachment_service.create_presigned_download_url(non_existing_attachment_id)
        assert f"Attachment with ID {non_existing_attachment_id} not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_confirm_upload_file_missing(
            self,
            attachment_service,
            owner_type,
            owner_id,
            original_filename,
            content_type,
            uploaded_by,
    ):
        storage_key = f"{owner_type}/{owner_id}/{uuid4()}.txt"
        confirm_request = ConfirmUploadRequest(
            storage_key=storage_key,
            original_filename=original_filename,
            content_type=content_type,
            owner_type=owner_type,
            owner_id=owner_id,
        )

        with pytest.raises(NotFoundError):
            await attachment_service.confirm_upload(confirm_request, uploaded_by)
