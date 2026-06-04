from uuid import UUID

from fastapi import APIRouter, status

from ..iam.dependencies import CurrentUserDep
from ..shared.domain.exceptions import NotFoundError
from .dependencies import AttachmentRepoDep, AttachmentServiceDep
from .mappers import map_attachment_to_response
from .schemas import (
    AttachmentResponse,
    ConfirmUploadRequest,
    PresignedDownloadResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)

router = APIRouter(prefix="/attachments", tags=["Медиа контент"])


@router.post(
    path="/presigned-upload",
    status_code=status.HTTP_200_OK,
    response_model=PresignedUploadResponse,
    summary="Получить presigned URL для загрузки",
    description="""\
    Создаёт подписанный URL на стороне хранилища (S3)
    для прямой загрузки файла с клиентской части.
    """
)
async def create_presigned_upload_url(
        request: PresignedUploadRequest, service: AttachmentServiceDep,
) -> PresignedUploadResponse:
    return await service.create_presigned_upload_url(request)


@router.post(
    path="/confirm-upload",
    status_code=status.HTTP_201_CREATED,
    response_model=AttachmentResponse,
    summary="Подтвердить загрузку и создать вложение"
)
async def confirm_upload(
        current_user: CurrentUserDep, request: ConfirmUploadRequest, service: AttachmentServiceDep
) -> AttachmentResponse:
    return await service.confirm_upload(request, uploaded_by=current_user.user_id)


@router.get(
    path="/{attachment_id}/presigned-download",
    status_code=status.HTTP_200_OK,
    response_model=PresignedDownloadResponse,
    summary="Получить presigned URL для скачивания"
)
async def get_presigned_download_url(
        attachment_id: UUID, service: AttachmentServiceDep
) -> PresignedDownloadResponse:
    return await service.create_presigned_download_url(attachment_id)


@router.get(
    path="/{attachment_id}",
    status_code=status.HTTP_200_OK,
    response_model=AttachmentResponse,
    summary="Получение информации и файле"
)
async def get_attachment(attachment_id: UUID, repository: AttachmentRepoDep) -> AttachmentResponse:
    attachment = await repository.read(attachment_id)
    if attachment is None:
        raise NotFoundError(f"Attachment with ID {attachment_id} not found")
    return map_attachment_to_response(attachment)


"""@router.delete(
    path="/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить файл (Soft-delete)"
)
async def delete_attachment(attachment_id: UUID, repository: AttachmentRepoDep) -> None:
    ...


@router.get(
    path="/owner/{owner_type}/{owner_id}",
    status_code=status.HTTP_200_OK,
    response_model=...,
    summary="Получение всех файлов владельца"
)
async def get_owner_attachments(owner_type: str, owner_id: UUID) -> ...: ..."""
