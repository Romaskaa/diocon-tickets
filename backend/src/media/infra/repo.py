from uuid import UUID

from sqlalchemy import select

from ...shared.infra.repos import ModelMapper, SqlAlchemyRepository
from ..domain.entities import Attachment
from .models import AttachmentOrm


class AttachmentMapper(ModelMapper):
    @staticmethod
    def to_entity(model: AttachmentOrm) -> Attachment:
        return Attachment(
            id=model.id,
            updated_at=model.updated_at,
            created_at=model.created_at,
            original_filename=model.original_filename,
            mime_type=model.mime_type,
            size_bytes=model.size_bytes,
            storage_key=model.storage_key,
            owner_type=model.owner_type,
            owner_id=model.owner_id,
            is_public=model.is_public,
            uploaded_at=model.uploaded_at,
            uploaded_by=model.uploaded_by,
        )

    @staticmethod
    def from_entity(entity: Attachment) -> AttachmentOrm:
        return AttachmentOrm(
            id=entity.id,
            updated_at=entity.updated_at,
            created_at=entity.created_at,
            original_filename=entity.original_filename,
            mime_type=entity.mime_type,
            size_bytes=entity.size_bytes,
            storage_key=entity.storage_key,
            owner_type=entity.owner_type,
            owner_id=entity.owner_id,
            is_public=entity.is_public,
            uploaded_at=entity.uploaded_at,
            uploaded_by=entity.uploaded_by,
        )


class SqlAttachmentRepository(SqlAlchemyRepository[Attachment, AttachmentOrm]):
    model = AttachmentOrm
    model_mapper = AttachmentMapper

    async def get_by_storage_key(self, storage_key: str) -> Attachment | None:
        stmt = select(self.model).where(self.model.storage_key == storage_key)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return None if model is None else self.model_mapper.to_entity(model)

    async def get_by_owner(self, owner_type: str, owner_id: UUID) -> list[Attachment]:
        stmt = (
            select(self.model)
            .where(
                (self.model.owner_type == owner_type) &
                (self.model.owner_id == owner_id)
            )
        )
        results = await self.session.execute(stmt)
        models = results.scalars().all()
        return [self.model_mapper.to_entity(model) for model in models]
