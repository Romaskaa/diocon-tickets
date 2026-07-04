from typing import Annotated

from fastapi import Depends

from src.core.settings import S3_BUCKET_NAME, settings
from src.shared.dependencies import SessionDep

from .domain.ports import AttachmentRepository, Storage
from .infra.repo import SqlAttachmentRepository
from .infra.s3 import S3Storage
from .services import AttachmentService


def get_storage() -> Storage:
    return S3Storage(
        access_key=settings.yandex_cloud.access_key_id,
        secret_key=settings.yandex_cloud.secret_access_key,
        endpoint_url=settings.yandex_cloud.endpoint_url,
        bucket_name=S3_BUCKET_NAME,
    )


def get_attachment_repo(session: SessionDep) -> SqlAttachmentRepository:
    return SqlAttachmentRepository(session)


def get_attachment_service(
        session: SessionDep,
        storage: Storage = Depends(get_storage),
        repository: AttachmentRepository = Depends(get_attachment_repo),
) -> AttachmentService:
    return AttachmentService(session=session, storage=storage, repository=repository)


AttachmentRepoDep = Annotated[AttachmentRepository, Depends(get_attachment_repo)]
AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
